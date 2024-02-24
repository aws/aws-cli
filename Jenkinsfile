pipeline {
        agent any
        
        environment {
            PRISMA_API_URL="https://api4.prismacloud.io"
        }
        
        stages {
            stage('Checkout') {
              steps {
                  git branch: 'develop', url: 'https://github.com/Prismahacker77/aws-cli.git'
                  stash includes: '**/*', name: 'source'
              }
            }
            stage('Checkov') {
                steps {
                    withCredentials([string(credentialsId: 'PC_USER', variable: 'pc_user'),string(credentialsId: 'PC_PASSWORD', variable: 'pc_password')]) {
                        script {
                            docker.image('bridgecrew/checkov:latest').inside("--entrypoint=''") {
                              unstash 'source'
                              try {
                                  sh 'checkov -d . --use-enforcement-rules -o cli -o junitxml --output-file-path console,results.xml --bc-api-key ${pc_user}::${pc_password} --repo-id  Prismahacker77/aws-cli --branch develop'
                                  junit skipPublishingChecks: true, testResults: 'results.xml'
                              } catch (err) {
                                  junit skipPublishingChecks: true, testResults: 'results.xml'
                                  throw err
                              }
                            }
                        }
                    }
                }
            }
        }
        options {
            preserveStashes()
            timestamps()
        }
    }