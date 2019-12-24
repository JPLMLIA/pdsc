pipeline {
    agent any
    stages {
        stage('Clone') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/master']],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: 'key_pdsc',
                        url: 'git@github-fn.jpl.nasa.gov:COSMIC/COSMIC_PDSC.git']]
                ])
                dir('gh-pages') {
                    checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/gh-pages']],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: 'key_pdsc',
                        url: 'git@github-fn.jpl.nasa.gov:COSMIC/COSMIC_PDSC.git']]
                    ])
                }
            }
        }
        stage("Venv") {
            steps {
                // begin each build with a fresh virtualenv:
                sh '''#!/bin/bash
                    virtualenv venv_PDSC
                '''
            }
        }
        stage('Build') {
            steps {
                sh '''#!/bin/bash
                    source venv_PDSC/bin/activate
                    pip install --force-reinstall "pip<19.0.0"
                    pip install --process-dependency-links --upgrade .[devel]
                '''
            }
        }
        stage('Unit Tests') {
            steps {
                sh '''#!/bin/bash
                    source venv_PDSC/bin/activate
                    rm -f $WORKSPACE/test_reports/xml
                    mkdir -p $WORKSPACE/test_reports/xml
                    pytest -c test/unit.cfg \
                        --cov-report html:$WORKSPACE/test_reports/unit_coverage \
                        --junit-xml=$WORKSPACE/test_reports/xml/unit.xml
                '''
            }
        }
        stage('Functional Tests') {
            steps {
                sh '''#!/bin/bash
                    source venv_PDSC/bin/activate
                    pytest -c test/functional.cfg \
                        --cov-report html:$WORKSPACE/test_reports/functional_coverage \
                        --junit-xml=$WORKSPACE/test_reports/xml/functional.xml
                '''
            }
        }
        stage('Documentation Tests') {
            steps {
                withEnv([
                    'PDSC_DATABASE_DIR=/proj/COSMIC/pdsc_indices',
                    'PDSC_SERVER_HOST=localhost',
                    'PDSC_SERVER_PORT=7372'
                ]) {
                    sh '''#!/bin/bash
                        source venv_PDSC/bin/activate
                        pytest -c test/doctest.cfg
                        cd docs
                        make doctest
                    '''
                }
            }
        }
        stage('Build Documentation') {
            steps {
                sh '''#!/bin/bash
                    source venv_PDSC/bin/activate
                    cd docs
                    make html
                '''
            }
        }
        stage('Publish') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: false,
                    keepAll: false,
                    reportDir: 'test_reports/unit_coverage',
                    reportFiles: 'index.html',
                    reportName: 'Unit Test Coverage',
                    reportTitles: ''])
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: false,
                    keepAll: false,
                    reportDir: 'test_reports/functional_coverage',
                    reportFiles: 'index.html',
                    reportName: 'Functional Test Coverage',
                    reportTitles: ''])
                sh("cp -r docs/_build/html/* gh-pages/")
                dir('gh-pages') {
                    sh("rm -f run_ssh.sh")
                    sh("git add .")
                    sh("git diff --quiet --exit-code --cached || git commit -m 'publish documentation'")
                    withCredentials([sshUserPrivateKey(credentialsId: 'key_pdsc', keyFileVariable: 'GITHUB_KEY')]) {
                        sh 'echo ssh -i $GITHUB_KEY -l git -o StrictHostKeyChecking=no \\"\\$@\\" > run_ssh.sh'
                        sh 'chmod +x run_ssh.sh'
                        withEnv(['GIT_SSH=run_ssh.sh', 'PATH+CURRENTDIR=.']) {
                            sh 'git push origin HEAD:gh-pages'
                        }
                    }
                }
            }
        }
        stage('Post') {
            steps {
                junit allowEmptyResults: true, testResults: 'test_reports/xml/*.xml'
            }
        }
    }
}
