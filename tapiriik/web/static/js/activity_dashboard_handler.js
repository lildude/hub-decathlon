axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value


var app = new Vue({
    el: '#app',
    data() {
        return {
            activities:[],
        }
    },

    mounted() {
        // Retreiving the activities.
        axios.get("activities/fetch")
            .then(response => {this.activities = response.data})
            .catch(error => console.error(error))
    }
})
