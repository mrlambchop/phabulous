# Introduction

[Phabulous] is a crappy python client for phabricator

# Installation

    # One-time
    git clone https://github.com/mrlambchop/phabulous
    brew install pyenv pyenv-virtualenv
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    pyenv install -l
    # Pick the highest 2.x version
    export LATEST=$(pyenv install -l | grep '^\s*2\.' | tail -1)
    pyenv install $LATEST
    pyenv global $LATEST
    pyenv virtualenv $LATEST phabulous
    pyenv activate phabulous
    pip install -r src/requirements.txt

    # Run
    ./phab_cli.py
