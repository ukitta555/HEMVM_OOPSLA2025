module coin_wrapper::native_coin {
    use aptos_framework::coin;
    use std::string;
    use std::signer;
    use std::error;

    const ONLY_ADMIN: u64 = 0x1;

    struct DiemCoin has copy, store {}
    struct MintCapStore has key {
        cap: coin::MintCapability<DiemCoin>,
    }
    
    fun init_module(account: &signer) {
        let name = string::utf8(b"Diem Coin");
        let symbol = string::utf8(b"DMC");
        let decimals = 8;
        let (burn_cap, freeze_cap, mint_cap) = coin::initialize(account, name, symbol, decimals, false);
        coin::destroy_burn_cap(burn_cap);
        coin::destroy_freeze_cap(freeze_cap);
        let mint_cap_store = MintCapStore { cap: mint_cap };
        move_to(account, mint_cap_store);
    } 

    public entry fun mint(account: &signer, receiver: address, amount: u64) acquires MintCapStore {
        assert!(
            signer::address_of(account) == @coin_wrapper,
            error::permission_denied(ONLY_ADMIN),
        );
        let mint_cap = &borrow_global<MintCapStore>(signer::address_of(account)).cap;
        let coin = coin::mint<DiemCoin>(amount, mint_cap);
        coin::deposit(receiver, coin);
    }
}
