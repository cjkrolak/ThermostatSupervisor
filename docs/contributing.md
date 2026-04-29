# Introduction:
Thanks for considering developing to this project.  I welcome your contributions, diverse opinions, and the opportunity to learn through collaboration.  

I created this project primarily to provide a function that I needed (thermostat monitoring via remote access or onsite LAN), as well as provide a vehicle to experiment and learn new software development techniques.  This project includes application of:
* object-oriented python3 code
* client/server capability via flask
* unit and integration test structure
* code coverage measurement capability
* continuous integration via Azure pipelines and GitHub actions
* docker containerization.
* IoT applcation with raspberry pi

Future enhancements may include:
* continuous delivery and high availability via K8S.
* cloud hosting option
* multi-thermostat orchestration and control via machine learning algorithm.

I've written the code to work specifically with 4 different thermostat models I possess, but it should be fairly easily extendable to other thermostat types.  

# Ground Rules:
1. Contributors are respectful, considerate, collaborative, and open-minded.
2. Code is tested by author prior to pull requests.
3. GitFlow process is followed: code is developed off of `develop` branch tip, `develop` branch maintains viability through robust CI process, `main` branch is behind `develop` and uber-stable.
4. Test-driven development methodologies are used, test code is provided along with functionality.
5. Developers warranty their contributions, and are responsible for resolving issues with it.  Code is reliable, and developers continuously strive to improve code reliability. 
6. Standard conventions are followed, new code is consistent with incumbent code.  Python PEP8 style guide is followed.
7. issue tickets are singular, descriptive and comprehensive.
8. feature branches are descriptive in name and include issue # for traceability.
9. pull requests are descriptive including the description of fix, test results summary, and any helpful notes.
10. Project discussion should be kept within issue tickets, not taken off to email.

# Your First Contribution:
Check the issue backlog for issues of interest, or create your own issue.  Look for issues tagged with the "good first issue" tag.

1. Fork the repo.
2. Create feature branch in your fork, off of `develop`, name the branch with issue # and descriptive title, e.g. "33_fix_set_mode_bug_in_thermostat_x".
3. Write code, test code, rework code as needed.
4. Commit code to feature branch, add descriptive comments to pull request message: 1. description of fix, 2. test results summary.
5. Submit pull request back to `develop` branch of this project.  Add relevant reviewers to the pull request for code review.

# Getting started:
1. Install python3 and any dependencies listed in the readme file.
2. fork the repo, use `develop` branch for your training.
3. setup any required envirenment variables (see readme for details).
4. run code using emulator thermostat, functional checkout, integration test, supervise algorithm.
