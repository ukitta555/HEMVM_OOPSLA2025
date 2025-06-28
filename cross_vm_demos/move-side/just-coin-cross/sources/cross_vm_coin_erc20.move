module coin_wrapper::cross_vm_coin_erc20 {
    use aptos_framework::coin;
    use aptos_framework::coin::Coin;
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_framework::account;
    use aptos_framework::cross_vm;
    use aptos_std::from_bcs;
    use aptos_std::debug;
    use std::signer;
    use std::error;
    use std::bcs;
    use std::option;
    use std::string;
    use std::string::String;
    use std::vector;
    use aptos_std::type_info;

    const ONLY_ADMIN: u64 = 0x1;
    const ONLY_COIN_CALLER: u64 = 0x3;
    const INITIALIZE_COIN_TWICE: u64 = 0x4;
    const ONLY_MODULE_OWNER: u64 = 0x5;
    const UNSUPPRT_COIN: u64 = 0x6;
    const COIN_NOT_INITIALIZE: u64 = 0x7;
    const BAD_TOKEN_AMOUNT: u64 = 0x8;
    const INSUFFICIENT_BALANCE: u64 = 0x9;

    const RESOURCE_ACCOUNT_SEED: vector<u8> = b"coin_wrapper::native_vault::vault";
    const CASHIER_SEED: vector<u8> = b"coin_wrapper::native_vault::cashier";

    struct CallType has copy, store {}

    struct CapStore has key {
        resource_signer_cap: account::SignerCapability,
        cashier_signer_cap: account::SignerCapability,
        call_cap: cross_vm::CallEvmCap<CallType>,
    }

    struct MintBurnCapability<phantom CoinType> has store {
        mint: coin::MintCapability<CoinType>,
        burn: coin::BurnCapability<CoinType>,
    }

    struct CoinInfo<phantom CoinType> has key {
        evm_token_address: vector<u8>,
        mint_burn_cap: option::Option<MintBurnCapability<CoinType>>,
    }


    fun init_module(account: &signer) {
        let (_, resource_signer_cap) = account::create_resource_account(account, RESOURCE_ACCOUNT_SEED);
        let (_, cashier_signer_cap) = account::create_resource_account(account, CASHIER_SEED);

        let call_cap = cross_vm::initialize_cap<CallType>(account);
        let store = CapStore { resource_signer_cap: resource_signer_cap, call_cap: call_cap, cashier_signer_cap: cashier_signer_cap };
        move_to(account, store);

        debug::print(&string::utf8(b"Resource address"));
        debug::print(&resource_address());
        debug::print(&string::utf8(b"Cashier address"));
        debug::print(&cashier_address());
    }

    public entry fun initialize_mirror_coin<CoinType>(account: &signer, evm_address: vector<u8>, decimals: u8) acquires CapStore {
        assert!(
            !exists<CoinInfo<CoinType>>(resource_address()),
            error::already_exists(INITIALIZE_COIN_TWICE),
        );
        assert!(type_info::account_address(&type_info::type_of<CoinType>())==signer::address_of(account), error::permission_denied(ONLY_MODULE_OWNER));
        let (name, symbol) = query_erc20_metadata(evm_address);
        let (burn_cap, freeze_cap, mint_cap) = coin::initialize<CoinType>(account, name, symbol, decimals, false);
        coin::destroy_freeze_cap(freeze_cap);
        let coin_info = CoinInfo<CoinType> {
            evm_token_address: copy evm_address,
            mint_burn_cap: option::some(MintBurnCapability { mint: mint_cap, burn: burn_cap })
        };

        move_to(&resource_signer(), coin_info);
        coin::register<CoinType>(&resource_signer());
        coin::register<CoinType>(&cashier_signer());
        let encoded_decimal = bcs::to_bytes(&(coin::decimals<CoinType>() as u64));
        call_evm(b"handleLinkCoin", vector[raw_type<CoinType>(), encoded_decimal, type_name<CoinType>(), evm_address]);
    }

     public entry fun initialize_vault_coin<CoinType>() acquires CapStore{
        assert!(type_info::type_name<CoinType>() != string::utf8(b"0x1::aptos_coin::AptosCoin"), error::permission_denied(UNSUPPRT_COIN));
        assert!(
            !exists<CoinInfo<CoinType>>(resource_address()),
            error::already_exists(INITIALIZE_COIN_TWICE),
        );

        coin::register<CoinType>(&resource_signer());
        coin::register<CoinType>(&cashier_signer());

        let encoded_decimal = bcs::to_bytes(&(coin::decimals<CoinType>() as u64));
        let encoded_name = *string::bytes(&coin::name<CoinType>());
        let encoded_symbol = *string::bytes(&coin::symbol<CoinType>());
        let evm_address = call_evm(b"handleNewCoin", vector[raw_type<CoinType>(), encoded_decimal, type_name<CoinType>(), encoded_name, encoded_symbol]);

        let coin_info = CoinInfo<CoinType> {
            evm_token_address: evm_address,
            mint_burn_cap: option::none()
        };

        move_to(&resource_signer(), coin_info);
    }

    public fun evm_token_address<CoinType>(): vector<u8> acquires CoinInfo {
        borrow_global<CoinInfo<CoinType>>(resource_address()).evm_token_address
    }

    public fun query_erc20_metadata(evm_address: vector<u8>): (String, String) acquires CapStore {
        let name = string::utf8(call_evm(b"queryErc20Name", vector[evm_address]));
        let symbol = string::utf8(call_evm(b"queryErc20Symbol", vector[evm_address]));
        (name, symbol)
    }

    public entry fun deposit_aptos_coin(account: &signer, evm_receiver: vector<u8>, amount: u64) acquires CapStore{
        // debug::print(&string::utf8(b"1. Cross coin transfer!"));
        let coin = coin::withdraw<AptosCoin>(account, amount);
        let call_cap = &borrow_global<CapStore>(@coin_wrapper).call_cap;
        let _return = cross_vm::call_evm(option::some(coin), evm_receiver, string::utf8(b""), vector::empty(), call_cap);
    }

    // Move -> EVM: cross_vm (Native Move Module) -> call_evm -> add coin to the balance of the EVM receiver -> ""
    // caveat: experiment uses an EOA as a recipient; 

    public entry fun deposit<CoinType>(account: &signer, evm_receiver: vector<u8>, amount: u64) acquires CoinInfo, CapStore {
        assert!(
            exists<CoinInfo<CoinType>>(resource_address()),
            error::invalid_argument(COIN_NOT_INITIALIZE),
        );
        // debug::print(&string::utf8(b"Balance:"));
        // debug::print(&coin::balance<CoinType>(signer::address_of(account)));
        let coin = coin::withdraw<CoinType>(account, amount);
        deposit_inner(coin, evm_receiver);
    }

    fun deposit_inner<CoinType>(coin: Coin<CoinType>, evm_receiver: vector<u8>) acquires CoinInfo, CapStore {
        let amount = burn_or_put_coin_in_bank(coin);
        call_evm(b"handleDeposit", vector[evm_receiver, bcs::to_bytes(&amount), raw_type<CoinType>()]);
    }

    fun burn_or_put_coin_in_bank<CoinType>(coin: Coin<CoinType>): u64 acquires CoinInfo {
        let maybe_cap = &borrow_global<CoinInfo<CoinType>>(resource_address()).mint_burn_cap;
        let amount = coin::value(&coin);
        if (option::is_some(maybe_cap)) {
            if (coin::value(&coin) == 0) {
                coin::destroy_zero(coin);
            } else {
                let cap = option::borrow(maybe_cap);
                coin::burn(coin, &cap.burn);
            };
        } else {
            coin::deposit(resource_address(), coin);
        };
        amount
    }

    public fun withdraw<CoinType>(receiver: address) acquires CoinInfo, CapStore {
        assert!(
            exists<CoinInfo<CoinType>>(resource_address()),
            error::invalid_argument(COIN_NOT_INITIALIZE),
        );

        let coin = withdraw_inner<CoinType>();
        coin::deposit(receiver, coin)
    }

    fun withdraw_inner<CoinType>(): Coin<CoinType> acquires CoinInfo, CapStore {
        let raw_amount = call_evm(b"handleWithdraw", vector[raw_type<CoinType>()]);
        let amount = from_bcs::to_u64(raw_amount);
        mint_coin_or_withdraw_from_bank(amount)
    }

    fun mint_coin_or_withdraw_from_bank<CoinType>(amount: u64): Coin<CoinType> acquires CoinInfo, CapStore {
        let maybe_cap = &borrow_global<CoinInfo<CoinType>>(resource_address()).mint_burn_cap;
        if (option::is_some(maybe_cap)) {
            let cap = option::borrow(maybe_cap);
            coin::mint(amount, &cap.mint)
        } else {
            coin::withdraw(&resource_signer(), amount)
        }
    }

    fun ihe_deposit<CoinType>(caller: vector<u8>, message: vector<vector<u8>>): vector<u8> acquires CoinInfo, CapStore {
        assert!(caller==x"cc166f312524cc88e2c16c3bdd5735a23376b1fb", ONLY_COIN_CALLER);

        let amount = from_bcs::to_u64(vector::pop_back(&mut message));
        let receiver = from_bcs::to_address(vector::pop_back(&mut message));

        let coin = mint_coin_or_withdraw_from_bank(amount);
        coin::deposit<CoinType>(receiver, coin);

        b""
    }

    fun ihe_withdraw<CoinType>(caller: vector<u8>, _message: vector<vector<u8>>): vector<u8> acquires CoinInfo, CapStore {
        assert!(caller==x"cc166f312524cc88e2c16c3bdd5735a23376b1fb", ONLY_COIN_CALLER);

        let coin = claim_coin_from_cashier<CoinType>();
        let amount = burn_or_put_coin_in_bank(coin);

        bcs::to_bytes(&amount)
    }

    fun resource_signer(): signer acquires CapStore {
        let cap = &borrow_global<CapStore>(@coin_wrapper).resource_signer_cap;
        account::create_signer_with_capability(cap)
    }

    public fun resource_address(): address {
        account::create_resource_address(&@coin_wrapper, RESOURCE_ACCOUNT_SEED)
    }


    fun cashier_signer(): signer acquires CapStore {
        let cap = &borrow_global<CapStore>(@coin_wrapper).cashier_signer_cap;
        account::create_signer_with_capability(cap)
    }

    public fun cashier_address(): address {
        account::create_resource_address(&@coin_wrapper, CASHIER_SEED)
    }

    fun call_evm(func_name: vector<u8>, params: vector<vector<u8>>): vector<u8> acquires CapStore {
        let handler = x"cc166f312524cc88e2c16c3bdd5735a23376b1fb";
        let call_cap = &borrow_global<CapStore>(@coin_wrapper).call_cap;
        cross_vm::call_evm(option::none(), handler, string::utf8(func_name), params, call_cap)
    }

    fun claim_coin_from_cashier<CoinType>(): Coin<CoinType> acquires CapStore {
        let amount = coin::balance<CoinType>(cashier_address());
        coin::withdraw<CoinType>(&cashier_signer(), amount)
    }

    fun claim_coin_from_address<CoinType>(address: &signer): Coin<CoinType> {
        let amount = coin::balance<CoinType>(signer::address_of(address));
        coin::withdraw<CoinType>(address, amount)
    }


    public fun raw_type<CoinType>(): vector<u8> {
        type_info::encoded_type_tag<CoinType>()
    }

    public fun type_name<CoinType>(): vector<u8> {
        *string::bytes(&type_info::type_name<CoinType>())
    }

    fun to_str(bytes: vector<u8>): String {
        string::utf8(bytes)
    }

    public entry fun transfer<CoinType>(account: &signer, receiver: address, amount: u64) {
        coin::deposit(receiver, coin::withdraw<CoinType>(account, amount));
    }

    public entry fun transfer_native(account: &signer, receiver: address, amount: u64) {
        debug::print(&string::utf8(b"Balance before:"));
        debug::print(&coin::balance<AptosCoin>(signer::address_of(account)));
        
        let coin = coin::withdraw<AptosCoin>(account, amount);
        debug::print(&string::utf8(b"Withdrew successfully!"));
        
        coin::deposit(receiver, coin);
        debug::print(&string::utf8(b"Deposited successfully!"));

        debug::print(&string::utf8(b"Balance after:"));
        debug::print(&coin::balance<AptosCoin>(signer::address_of(account)));
    }

    public fun ihe_fake(caller: vector<u8>, message: vector<vector<u8>>): vector<u8> { b"" }
}