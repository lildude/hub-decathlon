from django.urls import include, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
import os

from tapiriik.web import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    re_path(r'^$', views.dashboard, name='dashboard'),
    re_path(r'^auth/redirect/(?P<service>[^/]+)$', views.oauth.authredirect, {}, name='oauth_redirect', ),
    re_path(r'^auth/redirect/(?P<service>[^/]+)/(?P<level>.+)$', views.oauth.authredirect, {}, name='oauth_redirect', ),
    re_path(r'^auth/return/(?P<service>[^/]+)$', views.oauth.authreturn, {}, name='oauth_return', ),
    re_path(r'^auth/return/(?P<service>[^/]+)/(?P<level>.+)$', views.oauth.authreturn, {}, name='oauth_return', ),  # django's URL magic couldn't handle the equivalent regex
    re_path(r'^auth/login/(?P<service>.+)$', views.auth_login, {}, name='auth_simple', ),
    re_path(r'^auth/login-ajax/(?P<service>.+)$', views.auth_login_ajax, {}, name='auth_simple_ajax', ),
    re_path(r'^auth/persist-ajax/(?P<service>.+)$', views.auth_persist_extended_auth_ajax, {}, name='auth_persist_extended_auth_ajax', ),
    re_path(r'^auth/disconnect/(?P<service>.+)$', views.auth_disconnect, {}, name='auth_disconnect', ),
    re_path(r'^auth/disconnect-ajax/(?P<service>.+)$', views.auth_disconnect_ajax, {}, name='auth_disconnect_ajax', ),
    re_path(r'^auth/disconnect-do/(?P<service>.+)$', views.auth_disconnect_do, {}, name='auth_disconnect_do', ),
    re_path(r'^auth/auth_disconnect_garmin_health$', views.auth_disconnect_garmin_health, {}, name='auth_disconnect_garmin_health', ),
    re_path(r'^auth/logout$', views.auth_logout, {}, name='auth_logout', ),

    re_path(r'^account/setemail$', views.account_setemail, {}, name='account_set_email', ),
    re_path(r'^account/settz$', views.account_settimezone, {}, name='account_set_timezone', ),
    re_path(r'^account/configure$', views.account_setconfig, {}, name='account_set_config', ),

    re_path(r'^account/rollback/?$', views.account_rollback_initiate, {}, name='account_rollback_initiate', ),
    re_path(r'^account/rollback/(?P<task_id>.+)$', views.account_rollback_status, {}, name='account_rollback_status', ),

    re_path(r'^rollback$', views.rollback_dashboard, {}, name='rollback_dashboard', ),

    re_path(r'^configure/save/(?P<service>.+)?$', views.config.config_save, {}, name='config_save', ),
    re_path(r'^configure/dropbox$', views.config.dropbox, {}, name='dropbox_config', ),
    re_path(r'^configure/flow/save/(?P<service>.+)?$', views.config.config_flow_save, {}, name='config_flow_save', ),
    re_path(r'^settings/?$', views.settings, {}, name='settings_panel', ),

    # re_path(r'^dropbox/browse-ajax/?$', views.dropbox.browse, {}, name='dropbox_browse_ajax', ),

    re_path(r'^sync/status$', views.sync_status, {}, name='sync_status'),
    re_path(r'^sync/activity$', views.sync_recent_activity, {}, name='sync_recent_activity'),
    re_path(r'^sync/schedule/now$', views.sync_schedule_immediate, {}, name='sync_schedule_immediate'),
    re_path(r'^sync/errors/(?P<service>[^/]+)/clear/(?P<group>.+)$', views.sync_clear_errorgroup, {}, name='sync_clear_errorgroup'),

    re_path(r'^activities$', views.activities_dashboard, {}, name='activities_dashboard'),
    re_path(r'^activities/fetch$', views.activities_fetch_json, {}, name='activities_fetch_json'),

    re_path(r'^sync/remote_callback/trigger_partial_sync/(?P<service>.+)$', views.sync_trigger_partial_sync_callback, {}, name='sync_trigger_partial_sync_callback'),


    re_path(r'^status/$', views.server_status, {}, name='server_status'),
    re_path(r'^status_elb/$', views.server_status_elb, {}, name='server_status_elb'),

    re_path(".well-known/security.txt", views.server_securitytxt, {}, name='server_securitytxt'),

    re_path(r'^supported-activities$', views.supported_activities, {}, name='supported_activities'),
    # re_path(r'^supported-services-poll$', 'tapiriik.web.views.supported_services_poll', {}, name='supported_services_poll'),

    # re_path(r'^payments/claim$', 'tapiriik.web.views.payments_claim', {}, name='payments_claim'),
    # re_path(r'^payments/claim-ajax$', 'tapiriik.web.views.payments_claim_ajax', {}, name='payments_claim_ajax'),
    # re_path(r'^payments/promo-claim-ajax$', 'tapiriik.web.views.payments_promo_claim_ajax', {}, name='payments_promo_claim_ajax'),
    # re_path(r'^payments/claim-wait-ajax$', 'tapiriik.web.views.payments_claim_wait_ajax', {}, name='payments_claim_wait_ajax'),
    # re_path(r'^payments/claim/(?P<code>[a-f0-9]+)$', 'tapiriik.web.views.payments_claim_return', {}, name='payments_claim_return'),
    # re_path(r'^payments/return$', 'tapiriik.web.views.payments_return', {}, name='payments_return'),
    # re_path(r'^payments/confirmed$', 'tapiriik.web.views.payments_confirmed', {}, name='payments_confirmed'),
    # re_path(r'^payments/ipn$', 'tapiriik.web.views.payments_ipn', {}, name='payments_ipn'),
    # re_path(r'^payments/external/(?P<provider>[^/]+)/refresh$', 'tapiriik.web.views.payments_external_refresh', {}, name='payments_external_refresh'),

    re_path(r'^ab/begin/(?P<key>[^/]+)$', views.ab_web_experiment_begin, {}, name='ab_web_experiment_begin'),

    re_path(r'^privacy$', TemplateView.as_view(template_name='static/privacy.html'), name='privacy'),
    re_path(r'^faq$', TemplateView.as_view(template_name='static/faq.html'), name='faq'),
    re_path(r'^credits$', TemplateView.as_view(template_name='static/credits.html'), name='credits'),
    re_path(r'^contact$', TemplateView.as_view(template_name='static/contact.html'), name='contact'),
    # Examples:
    # re_path(r'^$', 'tapiriik.views.home', name='home'),
    # re_path(r'^tapiriik/', include('tapiriik.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # re_path(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # re_path(r'^admin/', include(admin.site.urls)),



    #########################
    # API Related
    #########################
    re_path(r'^api/providers$', views.providers, {}, name='providers'),

    #########################
    # Error management
    #########################
    re_path(r'^fail_to_disconnect_svc$', TemplateView.as_view(template_name='service_disconnect_failure.html'), name='fail_to_disconnect_svc')
]



if 'DIAG_ENABLED' in os.environ and os.environ['DIAG_ENABLED'] == 'True':
    urlpatterns_diag = [
        re_path(r'^diagnostics/$', views.diag_dashboard, {}, name='diagnostics_dashboard'),
        re_path(r'^diagnostics/queue$', views.diag_queue_dashboard, {}, name='diagnostics_queue_dashboard'),
        re_path(r'^diagnostics/errors$', views.diag_errors, {}, name='diagnostics_errors'),
        re_path(r'^diagnostics/error/(?P<error>.+)$', views.diag_error, {}, name='diagnostics_error'),
        re_path(r'^diagnostics/graphs$', views.diag_graphs, {}, name='diagnostics_graphs'),
        re_path(r'^diagnostics/user/unsu$', views.diag_unsu, {}, name='diagnostics_unsu'),
        re_path(r'^diagnostics/userlookup/$', views.diag_user_lookup, {}, name='diagnostics_user_lookup'),
        re_path(r'^diagnostics/connection/$', views.diag_connection, {}, name='diagnostics_connection'),
        re_path(r'^diagnostics/api/connections/search$', views.diag_api_search_connection, {}, name='diagnostics_search_connections'),
        re_path(r'^diagnostics/api/connections/(?P<connection_id>[\da-zA-Z]*)$', views.diag_api_connection_by_id, {}, name='diagnostics_get_connection_by_id'),
        re_path(r'^diagnostics/api/user_activities$', views.diag_api_user_activities, {}, name='diagnostics_dashboard'),
        re_path(r'^diagnostics/user/(?P<user>[\da-zA-Z]+)/activities$', views.diag_user_activities, {}, name='diagnostics_user_activities'),
        re_path(r'^diagnostics/user/(?P<user>.+)$', views.diag_user, {}, name='diagnostics_user'),
        re_path(r'^diagnostics/payments/$', views.diag_payments, {}, name='diagnostics_payments'),
        re_path(r'^diagnostics/ip$', views.diag_ip, {}, name='diagnostics_ip'),
        re_path(r'^diagnostics/stats$', views.diag_stats, {}, name='diagnostics_stats'),
        re_path(r'^diagnostics/login$', views.diag_login, {}, name='diagnostics_login'),
    ]

    urlpatterns += urlpatterns_diag



urlpatterns += staticfiles_urlpatterns()
