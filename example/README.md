# Example

This is an example Ansible directory, where you would organize all of your playbooks, var_files, and roles.


### This is an example usage of the wrapper script, that pipes in the output of your original dynamic inventory file.

```
$ ansible-playbook -i inventories/wrapper.sh playbook.yml --extra-vars "env_prod"
```

