#include "Repository.hpp"
#include <filesystem>
#include <stdexcept>

#include <fstream>

Repository::Repository(const std::string& path){
    m_worktree = path;
    m_vcsdir = path + "\\.VCS++\\";  
    std::cout << m_vcsdir << " : Path for the VCS++ !" << std::endl;
}

Repository::~Repository(){
    
}

std::string Repository::RepositoryPath(const std::vector<std::string>& path, bool create){
    std::string result(m_vcsdir);
    for(const auto& elem : path){
        result = result + "\\" + elem;
    }

    if(create){
        std::filesystem::create_directories(result);
        std::cout << "Created a Directory named " << result << "." << std::endl;
    }

    return result;
}

void Repository::InitRepository(){
    if(!std::filesystem::is_directory(m_worktree)){ 
        std::string exp = m_worktree + " is not a directory !";
        throw std::runtime_error(exp);
    }

    if(std::filesystem::exists(m_vcsdir)){  
        if(!std::filesystem::is_empty(m_vcsdir)){
            std::string exp = m_vcsdir + " already exists and contains files !";
            throw std::runtime_error(exp);
        }
    }

    RepositoryPath({"branches"}, true);
    RepositoryPath({"objects"}, true);
    RepositoryPath({"refs", "tags"}, true);
    RepositoryPath({"refs", "heads"}, true);

    // VCS++/description
    std::ofstream desc{m_vcsdir + "description"};
    desc.write("Unnamed repository; edit this file 'description' to name the repository.\n", 1024);
    desc.close();

    // VCS++/HEAD
    std::ofstream head(m_vcsdir + "HEAD");
    head.write("ref: refs/heads/master\n", 1024);
    head.close();


    // VCS++/config
    // std::ofstream conf(m_vcsdir + "config");
    // maybe create a ConfigParser like python


}