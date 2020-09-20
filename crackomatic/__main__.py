def init(args=None):
    from .args import parse_args
    args = parse_args(args)

    from .models import init_db
    init_db('sqlite:///' + args.db_path)

    from .log import init_log
    sql = (args.operation != 'audit')
    init_log('DEBUG' if args.debug else 'INFO', sql=sql)

    return args


def run_web(args):
    import sys
    from logging import getLogger

    from gevent.pywsgi import WSGIServer

    from .flask import app, backend
    from .cert import load_selfsigned_cert

    log = getLogger(__name__)

    try:
        if args.key and args.cert:
            key, cert = args.key, args.cert
        else:
            log.warning(
                "No certifcate or key specified; using a"
                " selfsigned certificate. You should supply a"
                " proper certificate!"
            )
            key, cert = load_selfsigned_cert(args.local_address)

        app.config.update(dict(
            debug=args.debug,
            host=args.local_address,
            port=args.port,
            use_reloader=False,
        ))

        http_server = WSGIServer(
            (args.local_address, args.port),
            app,
            keyfile=key,
            certfile=cert,
            #  log=log,  # This would clutter our database logs
        )
        http_server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        backend.clean_up()
        sys.exit()


def main(args=None):
    args = init(args)

    if args.operation == 'web':
        run_web(args)
    elif args.operation == 'audit':
        import json
        from .audit import get_audit_sample, print_audit_description, \
            perform_audit
        if args.sample:
            sample = get_audit_sample()
            return json.dumps(sample, indent=4, sort_keys=True)
        elif args.description:
            print_audit_description()
        else:
            perform_audit(args.audit_file, interactive=args.interactive)
    elif args.operation == 'user':
        from .user import perform_user_action
        perform_user_action(args.action, args.username)


if __name__ == "__main__":
    main()
