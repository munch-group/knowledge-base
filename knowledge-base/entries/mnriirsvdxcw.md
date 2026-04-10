```
lftp -e "set sftp:connect-program 'ssh -p 9910 -c aes128-cbc'; mirror --continue --use-pget-n=4 /rt38821 ./rt38821; quit" sftp://KMunch-001:pxukirkc@hgsc-sftp1.hgsc.bcm.tmc.edu
```