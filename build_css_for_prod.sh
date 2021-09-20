
echo "Compiling and pre-minifying the SCSS file"
sass --style=compressed --no-source-map ./tapiriik/web/dev_static/css/style.scss ./tapiriik/web/dev_static/css/dev_style.css
echo "Purging unused CSS classes from vitamin"
purgecss -c ./tapiriik/web/dev_static/js/purgecss.js