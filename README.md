# codx-junior
Your junior assistant for Full Stack Developers... without too much time to loose ;)

## Motivation

As a Full Stack Developer working for different custmers, I'm supposed to be able to deal with everything, know everything, and fix everything... ASAP!
> From front, to back, to database, cloud, DevOps...

and don't get me wrong, I love it! but it's a titan task, don't you? 

So I started developing codx-junior to have an AI that can manage all tedious and repetitive tasks in software development and IT. 

I want codx-junior to help me deal with projects I don't know and situations where `"the last developer left yesterday and there's no doc."` 

I want codx-junior to write better `code` than me, better `tests` than me, and, of course, keep `documentation` updated.

### Hello codx-junior

![image](https://github.com/user-attachments/assets/025b7177-3db8-4d6b-886d-4bb9fb037f77)



## PNRL: Play now read later

Default setup will run a docker container with codx-junior and will map codx-junior repor parent's path to connect with host's projects. 

### dev environment

#### docker
```sh
  git clone https://github.com/gbrian/codx-junior.git
  cd codx-junior
  # change `.env.dev` as needed
  # Set HOST_PROJECTS_ROOT_PATH to yor host project's path
  ########################################### 
  ## It's important have same path between 
  ## host project's and container 
  ###########################################
  HOST_PROJECTS_ROOT_PATH="$(dirname $PWD)" \
  HOST_USER="$(id -u):$(id -g)" \
  docker-compose -f docker-compose.dev.yaml up -d
```

#### bash
```sh
  git clone https://github.com/gbrian/codx-junior.git
  cd codx-junior
  # change `.env.dev` as needed
  source .env.dev
  bash installer.sh
  bash run_client.sh &
  bash run_api.sh &
```

After you should be able to access codx-junior at: 
http://localhost:9983

## codx-junior builtin features

### Knowledge
codx-junior uses RAG techniques to find revelant parts of the code for your tasks or giving support

![image](https://github.com/user-attachments/assets/fbbd1591-586b-47dc-9991-b7e392b8d38f)

### Tasks
codx-junior is agile and task based. Create task and polish it with codx-junior until your are ready to generate code

![image](https://github.com/user-attachments/assets/64aa5c7c-6c40-41bc-abdc-2f93a84b60c0)

### Wiki
Documentation is always the first part that gets oudated... not anymore. codx-junior will take care and keep it updated for you.

![image](https://github.com/user-attachments/assets/0e29b06f-94af-4177-bf31-038370e910c3)

### Personalize
Define how do you want codx-junior to perform, code styling, ...

#### Settings
![image](https://github.com/user-attachments/assets/d767b29b-f014-4d65-b351-c83aed40d622)

#### Profiles
![image](https://github.com/user-attachments/assets/60911bd2-d26f-4e82-bc32-a77c1b0c105e)


### Mentions (aka copilot)

Mentions allow you to reference specific parts of your project or codebase for easier management and collaboration. Below is a demonstration video on how to use mentions effectively:

To use mentions, simply include the `@codx-processing` tag followed by the specific instruction or note you want to add. For example:
```markdown
@codx-processing: --knowledge @codx-junior-api Add a link to webm video from "assets/codx_mentions_demo.webm". And explain about mentions and how to use it
```
This will notify the system to process the mention and make the necessary changes or additions.

### Code generation
Ofc... we are here for this :) so just press "code" button or use mentions to creat code


```           _                 _   _             
          (_)               | | (_)            
 _ __ ___  _  __ _ _ __ __ _| |_ _ _ __   __ _ 
| '_ ` _ \| |/ _` | '__/ _` | __| | '_ \ / _` |
| | | | | | | (_| | | | (_| | |_| | | | | (_| |
|_| |_| |_|_|\__, |_|  \__,_|\__|_|_| |_|\__, |
              __/ |                       __/ |
             |___/                       |___/ 
```
This project come from my fork of https://github.com/gpt-engineer-org/gpt-engineer - such a great project! ❤️- ...but that work was never merged to main branch because I followed different approach and ended up rewriting everything. Please try gpt-engineer as well, worth it!

Nowadays codx branch has nothing in common with gpt-enginner master so it's time to create a new project for it.
