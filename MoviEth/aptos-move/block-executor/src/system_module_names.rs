// Copyright (c) Aptos
// SPDX-License-Identifier: Apache-2.0
//! Names of modules, functions, and types used by Aptos System.

use aptos_types::account_config;
use move_core_types::{ident_str, identifier::IdentStr, language_storage::ModuleId};
use once_cell::sync::Lazy;

// Data to resolve basic account and transaction flow functions and structs
/// The ModuleId for the aptos block module
pub static BLOCK_MODULE: Lazy<ModuleId> = Lazy::new(|| {
    ModuleId::new(
        account_config::CORE_CODE_ADDRESS,
        ident_str!("block").to_owned(),
    )
});

pub static TIMESTAMP_MODULE: Lazy<ModuleId> = Lazy::new(|| {
    ModuleId::new(
        account_config::CORE_CODE_ADDRESS,
        ident_str!("timestamp").to_owned(),
    )
});

// TZ: TODO: remove these except for the block-related names
// Names for special functions and structs
pub const SCRIPT_PROLOGUE_NAME: &IdentStr = ident_str!("script_prologue");
pub const MULTI_AGENT_SCRIPT_PROLOGUE_NAME: &IdentStr = ident_str!("multi_agent_script_prologue");
pub const MODULE_PROLOGUE_NAME: &IdentStr = ident_str!("module_prologue");
pub const USER_EPILOGUE_NAME: &IdentStr = ident_str!("epilogue");
pub const BLOCK_PROLOGUE: &IdentStr = ident_str!("block_prologue");
pub const GET_BLOCK_HEIGHT_NAME: &IdentStr = ident_str!("get_current_block_height");
pub const GET_TIMESTAMP_NAME: &IdentStr = ident_str!("now_seconds");
