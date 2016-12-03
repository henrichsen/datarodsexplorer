from django.shortcuts import render
from django.http import JsonResponse
from tethys_sdk.gizmos import SelectInput, Button, TimeSeries
from model_objects import get_geoserver_url, get_wms_vars, get_datarods_png, get_datarods_tsb, \
    get_model_fences, get_model_options, get_var_dict, init_model
from utilities import create_map, create_select_model, create_plot_ctrls, create_map_date_ctrls, \
    create_years_list, load_tiff_ly, get_data_rod_plot, get_data_rod_plot2, get_data_rod_years
from json import dumps
from tethys_services.backends.hs_restclient_helper import get_oauth_hs
from requests import get
from tempfile import TemporaryFile
from ast import literal_eval


def home(request):
    """
    Controller for the app 'home' page.
    """

    init_model()

    model = get_model_options()[0][1]

    select_model = create_select_model(model)
    select_date, select_hour = create_map_date_ctrls(model)

    # Load map
    map_view, map_view_options = create_map()

    start_date1, end_date1, plot_button1 = create_plot_ctrls(model, 'plot')
    start_date2, end_date2, plot_button2 = create_plot_ctrls(model, 'plot2')
    select_model2 = SelectInput(display_text='',
                                name='model2',
                                multiple=False,
                                original=True,
                                options=get_model_options(),
                                attributes="onchange=oc_model2();"
                                )

    years_list = create_years_list(1979)
    select_years = SelectInput(display_text='',
                               name='years',
                               multiple=True,
                               original=False,
                               options=years_list,
                               attributes="onchange=oc_years();"
                               )

    plot_button3 = Button(display_text='Plot',
                          name='years',
                          style='',
                          icon='',
                          href='',
                          submit=False,
                          disabled=False,
                          attributes='onclick=createPlot(this.name);',
                          classes='btn-plot')

    # Context variables
    context = {
        'select_model': select_model,
        'MapView': map_view,
        'map_view_options': map_view_options,
        'select_date': select_date,
        'select_hour': select_hour,
        'MODEL_FENCES': dumps(get_model_fences()),
        'VAR_DICT': dumps(get_var_dict()),
        'DATARODS_PNG': dumps(get_datarods_png()),
        'DATARODS_TSB': dumps(get_datarods_tsb()),
        'WMS_VARS': dumps(get_wms_vars()),
        'start_date1': start_date1,
        'end_date1': end_date1,
        'plot_button1': plot_button1,
        'start_date2': start_date2,
        'end_date2': end_date2,
        'plot_button2': plot_button2,
        'select_model2': select_model2,
        'plot_button3': plot_button3,
        'select_years': select_years
    }

    return render(request, 'data_rods_explorer/app_base_dre.html', context)


def get_map_layer(request):
    context = {}
    if request.is_ajax() and request.method == 'POST':
        post_params = request.POST
        # If 'Display map' is clicked, load layers
        map_layers = load_tiff_ly(post_params)
        if map_layers:
            load_layer = map_layers[0]['options']['params']['LAYERS']
        else:
            load_layer = None

        context = {
            'load_layer': load_layer,
            'geoserver_url': get_geoserver_url()
        }

    return JsonResponse(context)


def plot(request):
    """
    Controller for the plot page.
    """
    post = request.POST
    context = {}

    # Plot
    if post and post['pointLonLat'] != '-9999':
        try:
            varname = get_wms_vars()[post['model']][post['variable']][1]
            varunit = get_wms_vars()[post['model']][post['variable']][2]
            point_lon_lat = post['pointLonLat']
            datarod_ts, datarods_urls_dict = get_data_rod_plot(post, point_lon_lat)
            timeseries_plot = TimeSeries(
                height='250px',
                width='100%',
                engine='highcharts',
                title=False,
                y_axis_title=varname,
                y_axis_units=varunit,
                series=[{
                    'name': '%s (Lon,Lat)' % point_lon_lat,
                    'data': datarod_ts
                }]
            )
            context = {
                'timeseries_plot': timeseries_plot,
                'datarods_urls_dict': datarods_urls_dict
            }
        except Exception as e:
            print str(e)
            if 'ERROR 999' in str(e):
                context = {
                    'error': str(e)
                }
            else:
                context = {
                    'error': 'An unknown error occured.'
                }

    return render(request, 'data_rods_explorer/plot.html', context)


def plot2(request):
    """
    Controller for the plot2 page.
    """
    post = request.POST

    # Plot
    if post and post['pointLonLat'] != '-9999':
        point_lon_lat = post['pointLonLat']
        datarod_ts, datarods_urls_dict = get_data_rod_plot2(post, point_lon_lat)
        timeseries_plot = {'y1_axis_units': get_wms_vars()[post['model']][post['variable']][2],
                           'y2_axis_units': get_wms_vars()[post['model2']][post['variable2']][2],
                           'series': datarod_ts}

        context = {
            'timeseries_plot': timeseries_plot,
            'plot2': True,
            'datarods_urls_dict': datarods_urls_dict
        }

        return render(request, 'data_rods_explorer/plot.html', context)


def years(request):
    """
    Controller for the 'years' page.
    """
    post = request.POST

    # Plot
    if post and post['pointLonLat'] != '-9999':
        varname = get_wms_vars()[post['model']][post['variable']][1]
        varunit = get_wms_vars()[post['model']][post['variable']][2]
        point_lon_lat = post['pointLonLat']
        datarod_ts, datarods_urls_dict = get_data_rod_years(post, point_lon_lat)
        timeseries_plot = TimeSeries(
            height='250px',
            width='100%',
            engine='highcharts',
            title=False,
            y_axis_title=varname,
            y_axis_units=varunit,
            series=datarod_ts
        )

        context = {
            'timeseries_plot': timeseries_plot,
            'datarods_urls_dict': datarods_urls_dict
        }

        return render(request, 'data_rods_explorer/plot.html', context)


def upload_to_hs(request):
    if request.is_ajax() and request.method == 'GET':
        res_id = None
        params = request.GET
        res_type = params.get('res_type', None)
        res_title = params.get('res_title', None)
        res_abstract = params.get('res_abstract', None)
        res_keywords = params.get('res_keywords', None)
        rods_endpoints = params.get('rods_endpoints', None)

        if rods_endpoints:
            rods_endpoints = literal_eval(str(rods_endpoints))

        try:
            hs = get_oauth_hs(request)
        except:
            return JsonResponse({
                'success': False,
                'message': 'You must be logged into the app through HydroShare to access this feature.'
            })

        num_endpoints = len(rods_endpoints)

        for i, url in enumerate(rods_endpoints):
            with TemporaryFile() as f:
                r = get(str(url))

                for chunk in r.iter_content(chunk_size=2048):
                    f.write(chunk)

                f.seek(0)
                filename = 'rods{i}.{ext}'.format(i='' if i == 0 else i + 1,
                                                  ext='nc' if 'netcdf' in str(url) else 'txt')
                # Netcdf resources can only have one file, so if there are more than one, create a GenericResource
                if res_type == 'NetcdfResource' and num_endpoints > 1:
                    res_type = 'GenericResource'

                # Resource should only be created the first time, then added to all subsequent times
                if i == 0:
                    res_id = hs.createResource(resource_type=str(res_type),
                                               title=str(res_title),
                                               resource_filename=filename,
                                               resource_file=f,
                                               abstract=str(res_abstract) if res_abstract else None,
                                               keywords=str(res_keywords).split(',') if res_keywords else None)
                else:
                    counter = 0
                    failed = True
                    while failed:
                        if counter == 15:
                            raise Exception
                        try:
                            hs.addResourceFile(res_id, resource_filename=filename, resource_file=f)
                            failed = False
                        except hs.HydroShareHTTPException as e:
                            if 'with method POST and params None' in str(e):
                                failed = True
                                counter += 1
                            else:
                                raise e

        return JsonResponse({
            'success': True,
            'res_id': res_id
        })
