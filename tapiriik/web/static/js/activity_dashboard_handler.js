axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value


var app = new Vue({
    el: '#app',
    data() {
        return {
            activities:[],
            services:[],
        }
    },

    mounted() {
        axios.get("api/providers")
            .then(response => this.services = response.data.providers)
            .catch(error => console.error(error))

        // Retreiving the activities.
        axios.get("activities/fetch")
            .then(response => {this.activities = response.data})
            .catch(error => console.error(error))

        // console.log(this.activities);
    },

    computed: {
    }

})
