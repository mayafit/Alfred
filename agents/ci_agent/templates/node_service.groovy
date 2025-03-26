pipeline {
    agent {
        docker {
            image 'node:16'
        }
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }
        
        stage('Lint') {
            steps {
                sh 'npm run lint'
            }
        }
        
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        
        stage('Build') {
            steps {
                sh 'npm run build'
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