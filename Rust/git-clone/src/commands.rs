use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

pub mod cat_file;
pub mod commit;
pub mod hash_list;
pub mod init;
pub mod read_tree;
pub mod write_tree;

pub use cat_file::*;
pub use commit::*;
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
    /// Create a new git repository
    Init,
    /// Create a new blob
    HashList(HashListArgs),
    /// Read a blob hash and retrieve contents
    CatFile(CatFileArgs),
    /// Build a blob tree
    WriteTree,
    /// Read a blob tree hash and retrieve subtrees/contents
    ReadTree(ReadTreeArgs),
    /// Create a commit
    Commit(CommitArgs),
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

#[derive(Args)]
pub struct CommitArgs {
    // Commit user name
    #[arg(long, short)]
    name: String,
    // Commit user email
    #[arg(long, short)]
    email: String,
    // Root tree hash
    #[arg(long, short)]
    hash: String,
    // Commit message
    #[arg(long, short)]
    message: String,
}
