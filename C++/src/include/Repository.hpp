#include <iostream>
#include <vector>
#include <string>

class Repository
{
private:
    std::string m_worktree;
    std::string m_vcsdir;

private:
    // Returns the path of m_vcsdir + all the elements
    std::string RepositoryPath(const std::vector<std::string>& element, bool create = false);

    public:
    Repository(const std::string& path);
    ~Repository();
    void InitRepository();
};