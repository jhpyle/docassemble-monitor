FROM debian:testing
RUN DEBIAN_FRONTEND=noninteractive \
apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive \
apt-get -q -y install \
apt-utils
RUN DEBIAN_FRONTEND=noninteractive \
apt-get -q -y install \
python3 \
nginx \
python3-dev \
python3-pip
RUN pip3 install uwsgi==2.0.19.1
COPY ./ ./app
WORKDIR ./app
RUN pip3 install -r requirements.txt
COPY ./nginx.conf /etc/nginx/sites-enabled/default
CMD service nginx start && uwsgi --uid=`id -u www-data` --gid=`id -g www-data` --enable-threads --uwsgi-socket=/tmp/uwsgi.sock --chmod-socket=666 --manage-script-name --mount /=app:app --workers=2 --master
