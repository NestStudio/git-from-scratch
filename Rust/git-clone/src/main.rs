use anyhow::Result;
use clap::Parser;

use crate::commands::{GitCli, process_git_init};

mod commands;

fn main() -> Result<()> {
    let git_cli = GitCli::parse();

    match git_cli.command {
        commands::Subcommands::Init => process_git_init()?,
    };

    Ok(())
}
