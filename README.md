# ansible-meta-dynamic-inventory

This script takes, as input, the output of a dynamic inventory script and reads in another file, called a Groupsfile, that allows dynamically creating new groups using any of Ansible's Pattern set notations, and then outputs an updated  version of the dynamic inventory that it received.

Ansible has a concept of _Inventory_, this is your listing/groupings of all of the machines in your infrastructure. Ansible allows for two types of inventories: _static_ and _dynamic_.

Here is an example of a simple static inventory:

```
[web]
10.0.1.2
10.0.1.3

[db]
10.2.0.2
10.2.0.3

[aws_us_east]

[aws_us_east:children]
web
db
```

This static inventory file describes two groups (web,db) with two hosts each, and a third group (aws_us_east) that is the union of web and db.  Static inventory works great if you have very few machines that never change, and it becomes virtually useless with the more hosts you have or the more _dynamic_ your inventory is.

### Dynamic inventory to the rescue!

Dynamic inventory is an executable script that inspects your infrastructure and dynamically creates groups out of them. If you're on AWS and using Ansible, then you're likely familiar with `ec2.py` [[link]](https://raw.githubusercontent.com/ansible/ansible/stable-1.9/plugins/inventory/ec2.py), a Python script that uses your AWS credentials to inspect EC2 and dynamically create groups based on VPCs, security groups, tags and much more.

### Ansible Patterns

Ansible also has this great feature that allows you to use set functions like union, intersection and difference on your host groups, called Patterns.  This allows for you to home in on _just the right_ group of hosts to operate on.

### The Rub

Ansible Patterns are limited to being used on the command line:

```
$ ansible tag_Env_prod:&tag_Service_web -m service -a "name=httpd state=restarted"
```

Or they can be used as the host specifier for a play:

```
---
- name: Install SomeService Role
  hosts: tag_Env_stg:!tag_Service_elk
  become: yes

  roles:
    - SomeService
```

This means that you _cannot_ use patterns in a static inventory file.  So the following does not work:

```
[web]
5.5.5.5
10.10.10.10

[prod]
10.10.10.10

[web_prod]

[web_prod:children]
web:&prod
```
This static inventory file attempts to create a `web_prod` group that only consists of machines in `web` && `prod`.

