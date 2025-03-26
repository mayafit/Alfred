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
        
        stage('Pack') {
            steps {
                sh 'dotnet pack --configuration Release --no-build --output ./packages'
            }
        }
        
        stage('Publish') {
            steps {
                sh 'dotnet nuget push ./packages/*.nupkg --source ${NUGET_SOURCE} --api-key ${NUGET_API_KEY}'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}