axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value

const syncCooldownInMs = 60000

var app = new Vue({
    el: '#app',
    data() {
        return {
            services: [],
            recentActivities:[],
            disconnectModalValues: {
                svcId: "",
                svcDisplayName: "",
                isOpen: false
            },
            isLoading: false,
            loadingSuccess: false,
            syncNowBtnDisabled: false,
        }
    },

    mounted() {
        // Retreiving the user connections.
        axios.get("api/providers")
            .then(response => this.services = response.data.providers)
            .catch(error => console.error(error))

        axios.get("sync/activity")
            .then(response => this.recentActivities = response.data)
            .catch(error => console.error(error))

        // To know on page loading the sync Status
        this.getStatus()
        // To refresh this status in the definite time in ms
        setInterval(this.getStatus, 10000);
    },

    computed: {
        isOneSvcConnected() {
            return this.services.find(x => x.isConnected == true) !== undefined
        }
    },
    methods: {
        isBidirectional: svc => svc.isSupplier && svc.isReceiver,
        syncNow(event) {
            this.syncNowBtnDisabled = true;
            axios.post("sync/schedule/now")
                .then(response => {
                    console.log("Sync now asked successfully")
                })
                .catch(error => {
                    if (error.response.status == 403) console.log("Sync now is in cooldown");
                    else console.error(error);
                })
        },

        getStatus() {
            axios.get("sync/status")
                .then(response => {
                    nextSync = new Date(response.data.NextSync)
                    lastSync = new Date(response.data.LastSync)

                    isSynchronizing = response.data.Synchronizing
                    // From the actual sync mechanism if the nextSync is prior now datetime, the user must be queued
                    isInQueue = nextSync <= new Date()
                    // Avoiding the user spamming the syncNow button
                    isInCooldown = (new Date() - lastSync) <= syncCooldownInMs

                    // We disable the syncNowButton if one of these conditions is met
                    this.syncNowBtnDisabled = isInQueue || isSynchronizing || isInCooldown
                })
                .catch(error => {
                    console.error("Can't get status\n" + error)
                })
        },


        openDisconnectModal(svcId) {
            // Just setting the string in the modal and displaying it.
            serviceHandled = this.services.find(x => x.id == svcId)
            this.disconnectModalValues = {
                svcId: svcId,
                svcDisplayName: serviceHandled.displayName,
                isOpen: true
            }
        },


        closeDisconnectModal() {
            // Closing the modal.
            this.disconnectModalValues.isOpen = false;
        },


        confirmDisconnection(svcId) {
            // Getting the service.
            serviceToDisconnect = this.services.find(x => x.id == svcId);

            // Closing "are you sure" modal and openning the loading one.
            this.closeDisconnectModal();
            this.isLoading = true;

            // Little ajax to disconnect the service
            axios.post("/auth/disconnect-ajax/" + serviceToDisconnect.id)
                .then(response => {
                    // If it's okay, time to display the success checkmark animation,
                    //      and showing to the user that the service is really disconnected.
                    this.loadingSuccess = true;
                    serviceToDisconnect.isConnected = false;

                    // Little "sleeping" before hiding the modal to let the animation play entirely.
                    setTimeout(() => {
                        this.isLoading = false;
                        this.loadingSuccess = false;
                    }, 1500);

                })
                .catch(error => {
                    // If there is an error just redirecting the user to a failure page.
                    location.href = "/fail_to_disconnect_svc"
                })
        },
    }

})
