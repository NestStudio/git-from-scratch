#include <iostream>
#include <vector>


class CommandLine
{
private:
    std::string                         m_command;
    std::vector<std::string>            m_args;

public:
    inline std::string                  GetCommand(){return m_command;}
    inline std::vector<std::string>     GetArguments(){return m_args;}
    bool                                Parse(int argc, char* argv[]);
};