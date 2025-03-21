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
                sh 'dotnet build --configuration Release --no-restore'
            }
        }
        
        stage('Test') {
            steps {
                sh 'dotnet test --no-restore --verbosity normal'
            }
        }
        
        stage('Pack') {
            steps {
                sh 'dotnet pack --no-build --configuration Release'
            }
        }
    }
}
