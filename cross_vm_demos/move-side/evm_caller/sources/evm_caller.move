module evm_caller::caller {
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_framework::cross_vm;
    use aptos_framework::coin;
    use std::string;
    use std::option;
    use std::vector;

    struct CallType has copy, store {}
    
    public entry fun call(account: &signer) {
        let cap = cross_vm::initialize_cap<CallType>(account);
        let receiver = x"cc166f312524cc88e2c16c3bdd5735a23376b1fb";
        let _return = cross_vm::call_evm(option::none(), receiver, string::utf8(b"handleMoveCall"), vector::singleton(b"Hi, Move Handler"), &cap);
    } 

    public entry fun transfer(account: &signer) {
        let cap = cross_vm::default_cap();
        let receiver = x"dddddddddddddddddddddddddddddddddddddddd";
        let coin = coin::withdraw<AptosCoin>(account, 1000_0000); // 0.1 coin
        let _return = cross_vm::call_evm(option::some(coin), receiver, string::utf8(b""), vector::empty(), &cap);
    }
}
