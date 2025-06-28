module evm_handler::hello {
    use aptos_std::type_info;
    use std::string;
    use std::bcs;

    fun ihe_hello(_caller: vector<u8>, _message: vector<vector<u8>>): vector<u8> {
        b"Hello, Ethereum Virtual Machine!"
    }

    fun ihe_hello_with_type<Type>(_caller: vector<u8>, _message: vector<vector<u8>>): vector<u8> {
        *string::bytes(&type_info::type_name<Type>())
    }

    fun ihe_hello_with_type_info<Type>(_caller: vector<u8>, _message: vector<vector<u8>>): vector<u8> {
        bcs::to_bytes(&type_info::type_of<Type>())
    }
}
