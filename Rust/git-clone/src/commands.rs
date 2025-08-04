use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

pub mod cat_file;
pub mod hash_list;
pub mod init;
pub mod read_tree;
pub mod write_tree;

pub use cat_file::*;
pub use hash_list::*;
pub use init::*;
pub use read_tree::*;
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
    ReadTree(ReadTreeArgs),
}

#[derive(Args)]
pub struct HashListArgs {
    // File to hash
    #[arg(long, short)]
    file: PathBuf,
}

#[derive(Args)]
pub struct CatFileArgs {
    // Hash of compressed file
    #[arg(long, short)]
    hash: String,
}

#[derive(Args)]
pub struct ReadTreeArgs {
    // Hash of root tree
    #[arg(long, short)]
    hash: String,
}
