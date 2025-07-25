#include "CommandLine.hpp"

bool CommandLine::Parse(int argc, char* argv[]){
    m_command = argv[1];
    for (size_t i = 2; i < argc; i++)
    {
        m_args.push_back(argv[i]);
    }
    return true;
}
