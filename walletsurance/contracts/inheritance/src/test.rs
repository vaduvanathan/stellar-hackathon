#![cfg(test)]
use super::*;
use soroban_sdk::{testutils::Ledger, Env};

#[test]
fn test_can_claim_and_beneficiary() {
    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(Inheritance, ());
    let client = inheritance::Client::new(&env, &contract_id);

    // Without deposit, can_claim is false
    let can = client.can_claim().unwrap();
    assert!(!can);
}
