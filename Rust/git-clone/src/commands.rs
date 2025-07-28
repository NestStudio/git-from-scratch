use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

pub mod hash_list;
pub mod init;

pub use hash_list::*;
pub use init::*;

#[derive(Parser)]
#[command(name = "sgit", version, about, long_about = None)]
pub struct GitCli {
    #[command(subcommand)]
    pub command: Subcommands,
}

#[derive(Subcommand)]
pub enum Subcommands {
    Init,
    HashList(HashListArgs),
}

#[derive(Args)]
pub struct HashListArgs {
    // File to hash
    #[arg(long, short)]
    file: PathBuf,
}
