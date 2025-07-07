# DESP-AAS Discussion

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [Deployment](#deployment)
- [License](#license)
- [Support](#support)

## Introduction

### What is the DESP-AAS Collaborative Platform?

DESP-AAS Collaborative Platform is a comprehensive service that enables users to collaborate on data science projects, share assets, and manage resources within a secure and scalable environment.

The Microservices that make up the Collaborative Platform project are the following:
- **Asset Management** Manages data assets, models, applications, and other resources
- **Storage** Manages file storage, Git repositories, and metadata including thumbnails and avatars
- **Search** Provides search capabilities across the platform's content
- **Group Management** Manages user groups and collaborative workspaces
- **Discussion** Handles communication and collaboration features
- **Moderation** Provides content moderation and quality control
- **Notification** Manages user notifications and alerts

### What is the Discussion Service?

The Discussion service is a microservice that enables collaborative communication around assets and projects within the DESP-AAS ecosystem. It provides the infrastructure and tools necessary for users to create, manage, and participate in discussions, topics, and posts related to assets and collaborative workspaces.

The Discussion service handles:
- **Discussion Management** Creating and managing discussion categories linked to assets
- **Topic and Post Management** Creating, editing, and retrieving topics and posts
- **Moderation Integration** Sending posts and topics for moderation
- **Integration** Working with other DESP-AAS microservices like Asset Management, Auth, and Notification

This service is a critical component of the DESP-AAS Collaborative Platform, enabling users to communicate, share knowledge, and collaborate effectively around their projects and assets.

## Prerequisites

Before you begin, ensure you have the following installed:
- **Git**
- **Docker** Docker is mainly used for the test suite, but can also be used to deploy the project via docker compose

## Installation

1. Clone the repository:
```bash
git clone https://github.com/acri-st/discussion.git
cd discussion
```

## Development

## Development Mode

### Standard local development

Setup environment
```bash
make setup
```

Start the development server:
```bash
make start
```

To clean the project and remove generated files, use:
```bash
make clean
```

## Contributing

Check out the **CONTRIBUTING.md** for more details on how to contribute.