#include <filesystem>



#include "VCS.hpp"
#include "CommandLine.hpp"



void VCS::run(int argc, char** argv){
    if(argc < 2){
        std::cout << "Usage Git++ <command> [<arguments>]" << std::endl;
        return;
    }

    CommandLine command;
    command.Parse(argc, argv);

    std::cout << command.GetCommand() << std::endl;
    for(auto elem : command.GetArguments()){
        std::cout << elem << std::endl;
    }


}

void init(){

}