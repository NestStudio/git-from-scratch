use anyhow::Result;
use clap::Parser;

use crate::commands::{GitCli, process_git_init, process_hash_list};

mod commands;

fn main() -> Result<()> {
    let git_cli = GitCli::parse();

    match git_cli.command {
        commands::Subcommands::Init => process_git_init()?,
        commands::Subcommands::HashList(hash_list_args) => process_hash_list(hash_list_args)?,
    };

    Ok(())
}
