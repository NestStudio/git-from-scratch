#include "VCS.hpp"
#include "CommandLine.hpp"
#include "Repository.hpp"

#include <filesystem>



void VCS::run(int argc, char** argv){
    if(argc < 2){
        std::cout << "Usage Git++ <command> [<arguments>]" << std::endl;
        return;
    }

    CommandLine command;
    command.Parse(argc, argv);

    path = std::filesystem::current_path().string();

    // std::cout << command.GetCommand() << std::endl;
    // for(auto elem : command.GetArguments()){
    //     std::cout << elem << std::endl;
    // }

    if(command.GetCommand() == "init"){
        init();
    }

}

void VCS::init(){
    Repository repo(path);
    repo.InitRepository();
}