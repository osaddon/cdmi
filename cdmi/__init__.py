from cdmi import CdmiMiddleware


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""

    conf = global_conf.copy()
    conf.update(local_conf)

    # Process the cdmi root and strip off leading or trailing space and slashes
    cdmi_root = conf.setdefault('cdmi_root', 'cdmi')
    cdmi_root = cdmi_root.lstrip('/ ').rstrip('/ ')
    conf['cdmi_root'] = cdmi_root
    conf['cdmi_root_length'] = len(cdmi_root.split('/'))
    conf.setdefault('cdmi_version_supported', '1.0.1')
    conf.setdefault('cdmi_capability_id', 'cdmi_capabilities')

    def cdmi_filter(app):
        return CdmiMiddleware(app, conf)

    return cdmi_filter
