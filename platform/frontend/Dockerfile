# 前端网关：nginx 静态托管 + /api 反代后端。
# 同源部署的好处：浏览器视角只有一个 80 端口，天然没有跨域问题，
# 本地开发的 CORS 配置只是开发期的便利，生产形态以网关收口。
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
# 注意两条 COPY 分开写：Docker 的多源 COPY 会把目录"打平"进目标
# （vendor/ 里的文件直接散进 html/，丢失 vendor/ 这层路径，
#  页面引用 vendor/*.js 会 404 被 try_files 回退成 index.html）
COPY index.html /usr/share/nginx/html/
COPY vendor/ /usr/share/nginx/html/vendor/

EXPOSE 80
