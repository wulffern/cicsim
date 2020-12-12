
FROM ubuntu

RUN apt-get update && apt-get install -y \
    git \
    python3.8 \
    python3-pip
RUN cd /home && git clone https://github.com/wulffern/cicsim.git
WORKDIR /home/cicsim/
RUN git pull
RUN git checkout -t origin/develop
RUN pip3 install -r requirements.txt --user
RUN pip3 install --no-deps -e  .
RUN echo "!#/bin/bash\n"
WORKDIR /home/cicsim/tests/sim/BFX1_CV
RUN make
WORKDIR /home/cicsim/tests/ip/
RUN cicsim ip SUN_TEST module_template.yaml