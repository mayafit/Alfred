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
        
        stage('Deploy to S3') {
            steps {
                withAWS(region: '${AWS_REGION}', credentials: 'aws-credentials') {
                    s3Upload(file: 'build', bucket: '${WEBSITE_BUCKET}', path: '${WEBSITE_PATH}')
                }
            }
        }
        
        stage('Invalidate CloudFront') {
            steps {
                withAWS(region: '${AWS_REGION}', credentials: 'aws-credentials') {
                    sh 'aws cloudfront create-invalidation --distribution-id ${DISTRIBUTION_ID} --paths "/*"'
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}