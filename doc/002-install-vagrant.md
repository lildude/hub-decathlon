### (the cool-kids way)

[Want to run tapiriik without Vagrant?](https://github.com/cpfair/tapiriik/wiki/Running-tapiriik-locally-without-Vagrant)

# Installation

1. Check out the tapiriik repo (the compressed archive will not do)
2. From the repo root, run `vagrant up`
3. Wait while a few hundred megabytes of virtual machine goodness is downloaded
4. Take some time to customize the `local_settings.py` file created in `tapiriik/`. You'll need to fill in the API keys for services you wish to connect to.

# Startup

1. Start the Django development server

   ```
   vagrant ssh
   python /vagrant/manage.py runserver 0.0.0.0:8000
   ```

2. Marvel at your shiny new instance of tapiriik available at `http://localhost:8000`
3. If you want to run synchronizations, you'll need to run a synchronization worker:

    ```
    vagrant ssh
    cd /vagrant/
    python ./sync_worker.py
    ```
and a synchronization scheduler:
    ```
    vagrant ssh
    cd /vagrant/
    python ./sync_scheduler.py
    ```

# Configuration

## Timezone database initialization

While synchronization is possible without the timezone database being populated, there may be errors in synchronized activities' times. Follow the instructions in `tz_ingest.py` to populate the database.


## Notes on running locally
* [The built-in diagnostics area](http://localhost:8000/diagnostics/) has a bunch of useful tools for administrating your local copy of tapiriik. I will leave the discovery of the various functionality as an exercise for the reader.
* To get your user ID, shift-click on the tapiriik logo, or click the email link at the bottom of the page (just like the production site, you have to be connected to >=1 service). You can use this to check out details of your specific account by visiting `localhost:8000/diagnostics/user/YOUR_USER_ID`
* Automatic synchronization is currently tied to the payment subsystem - just head to `auth/_init_.py` and make `HasActivePayment(user)` always return True
* You'll need to change the Strava OAuth return URL (the `redirect_uri` parameter of `UserAuthorizationURL` in strava.py) to match what your API credentials are set up for. Unfortunately (last time I checked) they don't allow localhost, so you may need to send the OAuth return to a different URL and manually replay said request against localhost.
* In case of using the Dropbox service, you'll need to [create and set up a new app](https://www.dropbox.com/developers/apps) within the Dropbox developers area (`Folder` to access just a folder, `Full` to be able to change working folder). In OAuth2, you'll need to configure the *redirect URI* for Dropbox to know how to continue the authentication process: `http://localhost:8000/auth/return/dropbox/normal`(for Folder) and `http://localhost:8000/auth/return/dropbox/full` (for Full).

## Why does Service X appear/not appear when running locally?
 * Some services are in the codebase but hidden on [tapiriik.com](https://tapiriik.com) because they are incomplete or not currently functional.
 * Some sites require that I not make their integration code open-source (they live in the `private.tapiriik...` modules). If you wish to integrate with these services, please contact them directly.
 
# [Back to summary](000-summary.md)
## [Back to install summary](001-install.md)
