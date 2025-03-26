pipeline {
    agent any
    
    tools {
        python 'Python 3.11'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Virtual Environment') {
            steps {
                sh 'python -m venv venv'
                sh '. venv/bin/activate'
                sh 'pip install --upgrade pip'
                sh 'pip install -r requirements.txt'
                sh 'pip install pytest pytest-cov flake8'
            }
        }
        
        stage('Code Quality') {
            steps {
                sh '. venv/bin/activate && flake8 --max-line-length=120 --exclude=venv .'
            }
        }
        
        stage('Test') {
            steps {
                sh '. venv/bin/activate && pytest --cov=. --cov-report=xml'
            }
            post {
                always {
                    junit 'pytest-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }
        
        stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
                sh 'docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest'
            }
        }
        
        stage('Push to Registry') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'docker-registry', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh 'docker push ${IMAGE_NAME}:${BUILD_NUMBER}'
                    sh 'docker push ${IMAGE_NAME}:latest'
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                sh 'kubectl apply -f k8s/staging'
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    input message: 'Approve deployment to production?'
                }
                sh 'kubectl apply -f k8s/production'
            }
        }
    }
    
    post {
        always {
            sh 'rm -rf venv'
        }
        success {
            slackSend channel: '#deployments',
                      color: 'good',
                      message: "Pipeline ${currentBuild.fullDisplayName} completed successfully."
        }
        failure {
            slackSend channel: '#deployments',
                      color: 'danger',
                      message: "Pipeline ${currentBuild.fullDisplayName} failed."
        }
    }
}