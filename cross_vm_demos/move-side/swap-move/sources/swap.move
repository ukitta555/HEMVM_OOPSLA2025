module swap_wrapper::swap {
    use aptos_framework::coin;
    use aptos_framework::account;
    use aptos_framework::cross_vm;
    use aptos_std::from_bcs;
    use aptos_std::debug;
    use aptos_std::option;
    use std::string;
    use std::vector;
    use pancake::router;
    use pancake::swap_utils;
    use coin_wrapper::cross_vm_coin;
    use pancake::swap::LPToken;

    struct CapStore has key {
        cashier_signer_cap: account::SignerCapability,
        call_cap: cross_vm::CallEvmCap<CallType>,
    }

    struct CallType has key, store {}

    const ONLY_ADMIN: u64 = 0x1;
    const ONLY_SWAP_CALLER: u64 = 0x2;

    const CASHIER_SEED: vector<u8> = b"swap_wrapper::swap::cashier";

    fun init_module(account: &signer) {
        let (_, cashier_signer_cap) = account::create_resource_account(account, CASHIER_SEED);
        let call_cap = cross_vm::initialize_cap<CallType>(account);

        let store = CapStore { cashier_signer_cap: cashier_signer_cap, call_cap: call_cap };
        move_to(account, store);

        debug::print(&string::utf8(b"Swap wrapper Cashier address"));
        debug::print(&cashier_address());
    } 

    fun cashier_signer(): signer acquires CapStore {
        let cap = &borrow_global<CapStore>(@swap_wrapper).cashier_signer_cap;
        account::create_signer_with_capability(cap)
    }

    public fun cashier_address(): address {
        account::create_resource_address(&@swap_wrapper, CASHIER_SEED)
    }

    public entry fun register_for_pool<X, Y>() acquires CapStore {
        if (swap_utils::sort_token_type<X, Y>()) {
            register_for_pool_inner<X, Y>();
        } else {
            register_for_pool_inner<Y, X>();
        }
    }

    fun register_for_pool_inner<X,Y>() acquires CapStore {
        let signer = cashier_signer();
        coin::register<X>(&signer);
        coin::register<Y>(&signer);
        coin::register<LPToken<X,Y>>(&signer);
        cross_vm_coin::initialize_vault_coin<LPToken<X,Y>>();

        let address = cross_vm_coin::evm_token_address<LPToken<X,Y>>();
        let handler = x"812cbbde09af8214a5c3adde18fcec9891196494";
        let func_name = b"handleSetLPToken";
        let params = vector[address, cross_vm_coin::raw_type<X>(), cross_vm_coin::raw_type<Y>()];
        let call_cap = &borrow_global<CapStore>(@swap_wrapper).call_cap;
        cross_vm::call_evm(option::none(), handler, string::utf8(func_name), params, call_cap);
    }

    fun sweep_out<CoinType>() acquires CapStore {
        let rest_balance = coin::balance<CoinType>(cashier_address());
        let receiver = cross_vm_coin::cashier_address();
        coin::transfer<CoinType>(&cashier_signer(), receiver, rest_balance);
    }


   fun ihe_swap_exact_input<X,Y>(caller: vector<u8>, message: vector<vector<u8>>): vector<u8> acquires CapStore {
        assert!(caller==x"812cbbde09af8214a5c3adde18fcec9891196494", ONLY_SWAP_CALLER);

        let out = from_bcs::to_u64(vector::pop_back(&mut message));
        let in = from_bcs::to_u64(vector::pop_back(&mut message));

        router::swap_exact_input<X,Y>(&cashier_signer(), in, out);
        sweep_out<Y>();
        b""
   }

   fun ihe_swap_exact_output<X,Y>(caller: vector<u8>, message: vector<vector<u8>>): vector<u8> acquires CapStore {
        assert!(caller==x"812cbbde09af8214a5c3adde18fcec9891196494", ONLY_SWAP_CALLER);

        let out = from_bcs::to_u64(vector::pop_back(&mut message));
        let in = from_bcs::to_u64(vector::pop_back(&mut message));

        router::swap_exact_output<X,Y>(&cashier_signer(), out, in);
        sweep_out<X>();
        sweep_out<Y>();
        b""
   }

   fun ihe_add_liquidity<X,Y>(caller: vector<u8>, message: vector<vector<u8>>): vector<u8> acquires CapStore {
        assert!(caller==x"812cbbde09af8214a5c3adde18fcec9891196494", ONLY_SWAP_CALLER);

        let outMin = from_bcs::to_u64(vector::pop_back(&mut message));
        let inMin = from_bcs::to_u64(vector::pop_back(&mut message));
        let out = from_bcs::to_u64(vector::pop_back(&mut message));
        let in = from_bcs::to_u64(vector::pop_back(&mut message));

        router::add_liquidity<X,Y>(&cashier_signer(), in, out, inMin, outMin);
        sweep_out<X>();
        sweep_out<Y>();
        if (swap_utils::sort_token_type<X, Y>()) {
            sweep_out<LPToken<X, Y>>();
        } else {
            sweep_out<LPToken<Y, X>>();
        };
        b""
   }

   fun ihe_remove_liquidity<X,Y>(caller: vector<u8>, _message: vector<vector<u8>>): vector<u8> acquires CapStore {
        assert!(caller==x"812cbbde09af8214a5c3adde18fcec9891196494", ONLY_SWAP_CALLER);

        let amount = if (swap_utils::sort_token_type<X, Y>()) {
            coin::balance<LPToken<X, Y>>(cashier_address())
        } else {
            coin::balance<LPToken<Y, X>>(cashier_address())
        };

        debug::print(&string::utf8(b"LP amount"));
        debug::print(&amount);

        router::remove_liquidity<X,Y>(&cashier_signer(), amount, 0, 0);
        sweep_out<X>();
        sweep_out<Y>();
        
        b""
   }
}