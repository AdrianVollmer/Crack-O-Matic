def test_email(mock_server):
    from common import email_config
    mock_server.reset()
    from crackomatic.email import send_mails

    send_mails(
        ['santa@northpole.com', 'nessie@lochness.net'],
        'crackomatic message',
        '''Hey there,

this is a test.

Cheers!''',
        email_config,
    )

    print(mock_server.received_messages)
    assert(mock_server.received_message_matching(
        ".*From: noreply@crackomatic.*"
        ".*Subject: crackomatic.*To: \"Undisc.*Bcc: santa@northpole.com,"
        " nessie@lochness.net.*Hey there,.*Cheers!.*"
    ))
    mock_server.reset()
    assert(mock_server.received_messages_count() == 0)

    send_mails(
        'santa@northpole.com',
        'crackomatic message',
        'Hey there',
        email_config,
    )
    print(mock_server.received_messages)
    assert(mock_server.received_message_matching(
        ".*Subject: crackomatic.*To: santa@northpole.com\n\n--.*"
    ))
    mock_server.reset()
    assert(mock_server.received_messages_count() == 0)
