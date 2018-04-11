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
                        credentialsId: 'github-cosmicfn',
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
        stage('Tests') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh '''#!/bin/bash
                            source venv_PDSC/bin/activate
                            mkdir -p $WORKSPACE/test_reports/html
                            rm -f $WORKSPACE/test_reports/xml
                            mkdir -p $WORKSPACE/test_reports/xml
                            pytest -c test/unit.cfg \
                                --cov-report html:$WORKSPACE/test_reports/html \
                                --junit-xml=$WORKSPACE/test_reports/xml/unit.xml
                        '''
                    }
                }
                stage('Functional Tests') {
                    steps {
                        sh '''#!/bin/bash
                            source venv_PDSC/bin/activate
                            rm -f $WORKSPACE/test_reports/xml
                            mkdir -p $WORKSPACE/test_reports/xml
                            pytest -c test/functional.cfg \
                                --junit-xml=$WORKSPACE/test_reports/xml/functional.xml
                        '''
                    }
                }
            }
        }
        stage('Publish') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: false,
                    keepAll: false,
                    reportDir: 'test_reports/html',
                    reportFiles: 'index.html',
                    reportName: 'Code Coverage Report',
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
