axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value

var app = new Vue({
    el: '#app',
    data() {
        return {
            services: [
                {
                    id: "strava",
                    displayName: "Strava",
                    isConnected: true,
                    isBidirectional: false,
                },
                {
                    id: "polarflow",
                    displayName: "Polar Flow",
                    isConnected: true,
                    isBidirectional: false,
                },
                {
                    id: "fitbit",
                    displayName: "Fitbit",
                    isConnected: false,
                    isBidirectional: true,
                },
                {
                    id: "garminhealth",
                    displayName: "Garmin Health",
                    isConnected: false,
                    isBidirectional: false,
                },
                {
                    id: "coros",
                    displayName: "Coros",
                    isConnected: false,
                    isBidirectional: false,
                }
            ],
            disconnectModalValues: {
                svcId: "",
                svdDisplayName: "",
                isOpen: false
            },
            isLoading: false,
            loadingSuccess: false,
        }
    },

    mounted(){
        axios.get("http://localhost:8000/api/providers")
            .then(response => this.services = response.data.providers)
            .catch(error => console.log(error))
    },

    computed: {
        isOneSvcConnected() {
            return this.services.find(x => x.isConnected == true) !== undefined
        }
    },
    methods: {
        openDisconnectModal(svcId) {
            serviceHandled = this.services.find(x => x.id == svcId)
            this.disconnectModalValues = {
                svcId: svcId,
                svdDisplayName: serviceHandled.displayName,
                isOpen: true
            }

        },

        closeDisconnectModal() {
            this.disconnectModalValues.isOpen = false;
        },

        confirmDisconnection(svcId) {
            serviceToDisconnect = this.services.find(x => x.id == svcId);
            this.closeDisconnectModal();

            this.isLoading = true;

            axios.post("http://localhost:8000/auth/disconnect-ajax/"+serviceToDisconnect.id)
                .then(response => {
                    console.log(response)
                    this.loadingSuccess = true;
                    serviceToDisconnect.isConnected = false;
                    setTimeout(() => {
                        this.isLoading = false;
                        this.loadingSuccess = false;
                    }, 1500);
                })
                .catch(error => {
                    location.href = "http://localhost:8000/fail_to_disconnect_svc"
                })
        },
    }

})
