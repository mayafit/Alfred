pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Restore') {
            steps {
                sh 'dotnet restore'
            }
        }
        
        stage('Build') {
            steps {
                sh 'dotnet build --configuration Release'
            }
        }
        
        stage('Test') {
            steps {
                sh 'dotnet test --configuration Release --no-build'
            }
        }
        
        stage('Publish') {
            steps {
                sh 'dotnet publish --configuration Release --no-build --output ./publish'
            }
        }
        
        stage('Docker Build') {
            steps {
                sh 'docker build -t ${DOCKER_REGISTRY}/${SERVICE_NAME}:${BUILD_TAG} .'
            }
        }
        
        stage('Docker Push') {
            steps {
                sh 'docker push ${DOCKER_REGISTRY}/${SERVICE_NAME}:${BUILD_TAG}'
            }
        }
        
        stage('Deploy') {
            steps {
                sh 'kubectl set image deployment/${SERVICE_NAME} ${SERVICE_NAME}=${DOCKER_REGISTRY}/${SERVICE_NAME}:${BUILD_TAG}'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}