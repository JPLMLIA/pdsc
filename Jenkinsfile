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
                sh '''#!/bin/bash
                    source venv_PDSC/bin/activate
                    pytest -c test/doctest.cfg
                '''
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
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: false,
                    keepAll: false,
                    reportDir: 'docs/_build/html',
                    reportFiles: 'index.html',
                    reportName: 'Documentation',
                    reportTitles: ''])
            }
        }
        stage('Post') {
            steps {
                junit allowEmptyResults: true, testResults: 'test_reports/xml/*.xml'
            }
        }
    }
}
