# How to run

pi 3
```bash
scp ncssm_clock.py raspberrypi@10.50.60.181:/home/raspberrypi/Documents/clock-tower
scp clock.service raspberrypi@10.50.60.181:/home/raspberrypi/Desktop
```

pi 4
```bash
scp ncssm_clock.py raspberrypi@10.50.12.69:/home/raspberrypi/Documents/clock-tower
scp clock.service raspberrypi@10.50.12.69:/home/raspberrypi/Desktop
```

## Note
When using SSH into the raspberry, we cant access root. It's best to `scp` the service file first to desktop, then sudo move it it to `/lib/systemd/system` via `ssh` or directly.