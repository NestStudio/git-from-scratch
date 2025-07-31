use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

pub mod cat_file;
pub mod hash_list;
pub mod init;
pub mod write_tree;

pub use cat_file::*;
pub use hash_list::*;
pub use init::*;
pub use write_tree::*;

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
    CatFile(CatFileArgs),
    WriteTree,
}

#[derive(Args)]
pub struct HashListArgs {
    // File to hash
    #[arg(long, short)]
    file: PathBuf,
}

#[derive(Args)]
pub struct CatFileArgs {
    // Hash used for decompression
    #[arg(long, short)]
    hash: String,
}
