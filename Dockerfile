FROM python:3.7.4-slim-buster

COPY sources.list /etc/apt/sources.list

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONIOENCODING=UTF-8
ENV TZ=Asia/Shanghai
ENV PROJECT_DIR=/data/blog/pblog

COPY ./ $PROJECT_DIR

#COPY ./.env_sample $PROJECT_DIR/.env

WORKDIR $PROJECT_DIR/source

#RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32

RUN apt update && apt install -y  apt-transport-https ca-certificates tzdata locales gcc && pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

RUN echo "Asia/Shanghai" > /etc/timezone && rm -f /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

ENV PYTHONPATH=$PYTHONPATH:$PROJECT_DIR

# 文件映射
#VOLUME /data/scrapy/source_spider

EXPOSE 5000

WORKDIR $PROJECT_DIR/source

CMD python manage.py runserver --host 0.0.0.0