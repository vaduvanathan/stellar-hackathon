#![no_std]
//! Walletsurance: Dead Man's Switch contract.
//! Lock funds; if depositor doesn't ping within timeout, beneficiary can claim.

use soroban_sdk::{
    contract, contractimpl, symbol_short, token, Address, Env, MuxedAddress, Symbol,
};

const KEY_DEPOSITOR: Symbol = symbol_short!("depositor");
const KEY_BENEFICIARY: Symbol = symbol_short!("benef");
const KEY_TOKEN: Symbol = symbol_short!("token");
const KEY_AMOUNT: Symbol = symbol_short!("amount");
const KEY_LAST_PING: Symbol = symbol_short!("last_ping");
const KEY_TIMEOUT: Symbol = symbol_short!("timeout");

#[contract]
pub struct Inheritance;

#[contractimpl]
impl Inheritance {
    /// Lock tokens and set up the switch. Caller must have approved this contract.
    /// `timeout_ledgers`: number of ledgers after last ping before claim is allowed.
    pub fn deposit(
        env: Env,
        depositor: Address,
        token: Address,
        amount: i128,
        beneficiary: Address,
        timeout_ledgers: u32,
    ) -> Result<(), soroban_sdk::Error> {
        depositor.require_auth();
        if amount <= 0 {
            return Err(soroban_sdk::Error::from_contract_error(1));
        }
        if timeout_ledgers == 0 {
            return Err(soroban_sdk::Error::from_contract_error(2));
        }

        let contract_id = env.current_contract_address();
        let token_client = token::Client::new(&env, &token);
        let to_muxed: MuxedAddress = contract_id.clone().into();
        token_client.transfer(&depositor, &to_muxed, &amount);

        let ledger = env.ledger().sequence();
        env.storage().instance().set(&KEY_DEPOSITOR, &depositor);
        env.storage().instance().set(&KEY_BENEFICIARY, &beneficiary);
        env.storage().instance().set(&KEY_TOKEN, &token);
        env.storage().instance().set(&KEY_AMOUNT, &amount);
        env.storage().instance().set(&KEY_LAST_PING, &ledger);
        env.storage().instance().set(&KEY_TIMEOUT, &timeout_ledgers);

        Ok(())
    }

    /// Reset the deadline. Only the depositor may call.
    pub fn ping(env: Env) -> Result<(), soroban_sdk::Error> {
        let depositor: Address = env
            .storage()
            .instance()
            .get(&KEY_DEPOSITOR)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;
        depositor.require_auth();

        let ledger = env.ledger().sequence();
        env.storage().instance().set(&KEY_LAST_PING, &ledger);
        Ok(())
    }

    /// Claim funds to beneficiary if timeout has passed. Callable by anyone (e.g. Python agent).
    pub fn claim(env: Env) -> Result<(), soroban_sdk::Error> {
        let last_ping: u32 = env
            .storage()
            .instance()
            .get(&KEY_LAST_PING)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;
        let timeout: u32 = env
            .storage()
            .instance()
            .get(&KEY_TIMEOUT)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;
        let current = env.ledger().sequence();
        if current < last_ping.saturating_add(timeout) {
            return Err(soroban_sdk::Error::from_contract_error(4)); // not yet expired
        }

        let beneficiary: Address = env
            .storage()
            .instance()
            .get(&KEY_BENEFICIARY)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;
        let token: Address = env
            .storage()
            .instance()
            .get(&KEY_TOKEN)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;
        let amount: i128 = env
            .storage()
            .instance()
            .get(&KEY_AMOUNT)
            .ok_or(soroban_sdk::Error::from_contract_error(3))?;

        let contract_id = env.current_contract_address();
        let token_client = token::Client::new(&env, &token);
        let to: MuxedAddress = beneficiary.clone().into();
        token_client.transfer(&contract_id, &to, &amount);

        // Clear vault so it cannot be claimed again
        env.storage().instance().remove(&KEY_DEPOSITOR);
        env.storage().instance().remove(&KEY_BENEFICIARY);
        env.storage().instance().remove(&KEY_TOKEN);
        env.storage().instance().remove(&KEY_AMOUNT);
        env.storage().instance().remove(&KEY_LAST_PING);
        env.storage().instance().remove(&KEY_TIMEOUT);

        Ok(())
    }

    /// View: can the vault be claimed? (timeout elapsed since last ping)
    pub fn can_claim(env: Env) -> Result<bool, soroban_sdk::Error> {
        let last_ping: u32 = match env.storage().instance().get(&KEY_LAST_PING) {
            Some(v) => v,
            None => return Ok(false),
        };
        let timeout: u32 = match env.storage().instance().get(&KEY_TIMEOUT) {
            Some(v) => v,
            None => return Ok(false),
        };
        let current = env.ledger().sequence();
        Ok(current >= last_ping.saturating_add(timeout))
    }

    /// View: beneficiary address
    pub fn beneficiary(env: Env) -> Result<Address, soroban_sdk::Error> {
        env.storage()
            .instance()
            .get(&KEY_BENEFICIARY)
            .ok_or(soroban_sdk::Error::from_contract_error(3))
    }
}

mod test;
