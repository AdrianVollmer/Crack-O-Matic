Why are weak passwords a problem?
=================================

One single weak password can endanger your entire environment. Attackers
love weak passwords. They can exploit the use of weak passwords or password
reuse in several scenarios. Let's take a close look at these scenarios and
what you, as an administrator, can do to protect your organization in each
of them. The focus is always Microsoft Active Directory Domain Services.


Online Password Guessing Attacks
--------------------------------

This is when you try to guess passwords against a live service. It may be
your internal Kerberos service or a service that you expose to the internet,
such as an Outlook Web Application, RDP or an SSH service. Now, these
shouldn't be exposed to the internet without multi-factor authentication in
the first place, but that's a different story.

The usual mitigation to online password guessing attacks (besides MFA) is to
only allow a few failed attempts before locking the account. But I see two
problems here.

The first problem is that it allows the attacker to make a few attempts. If
the password is sufficiently weak, this may be enough already. When you only
have three choices of password candidates, you use ``Summer2020``,
``Winter2019`` and ``<Name of your org>2020`` and spray these against all
Active Directory accounts. Note that these formally satisfy most password
policies. Depending on the security culture in your organization, it's not
unusual to compromise something like 2% of all accounts this way.
Sometimes, one of these accounts has privileges that allow for lateral
movement. Local admin permissions on just one machine could be enough to
compromise the entire domain.

The second problem is that you always need to find a balance between
mitigating guessing attacks and denial of service. Locking accounts forever
on the fifth attempt is a bad idea, because then an attacker can cripple
your organization until you manually unlock all accounts. (Hint: Don't do it
manually, there is a PowerShell one-liner that does this.)  So you set a
limited lockout duration, which means that after waiting for a couple of
minutes, our attacker gets a couple more attempts.

By the way, even a limited lockout duration could be a problem, if important
service accounts are being constantly locked out by someone. The trick here
is to define a fine-grained password policy for service accounts and remove the
lockout threshold. Just make sure that these accounts have super strong
passwords. Or simply use `Group Managed Service
Accounts <https://docs.microsoft.com/en-us/windows-server/security/group-managed-service-accounts/group-managed-service-accounts-overview>`_.


NTLM Authentication Hashes
--------------------------

A widespread authentication scheme in the Windows world is `NTLM
<https://support.microsoft.com/en-us/help/102716/ntlm-user-authentication-in-windows>`_.
It boils down to this: how can I prove to you, that I know a shared secret
that we both have without actually saying the secret? With NTLM, it works
like this: You give me a unique string (that somehow depends on the time and
your name) and ask me to digitally sign it. In this case, digitally signing
it means encrypting it with the secret. You do the same and compare the
results. If they match -- great, I have proved that I know our shared secret
and therefore am authenticated. The shared secret here is of course the
(hashed) password.

The disadvantage compared to modern asymmetric cryptography is that somebody
who listened in on our conversation or someone who just pretended to be the
person I actually wanted to speak to can take the unique string and attempt to
reproduce the signature by guessing the password. This can be done
`offline`, meaning no lockout thresholds apply. The only limiting factors
are the amount of computational power, time and -- the quality of the password.
We call this "cracking" a password.

As mentioned above, an attacker can obtain NTLM hashes by pretending to be a
service that the user wants to authenticate to. One way to achieve this is
to gain a Man-in-the-Middle position by spoofing responses to multicast name
resolution protocols such as NBT-NS or LLMNR. `Responder
<https://github.com/lgandx/Responder>`_ does this
conveniently for you. Spoofing ARP replies or sniffing on wireless networks
can also work. In these cases the attacker needs to be inside your
network already. Another way is to send somebody a message containing a link
to a service or an image on a server that requests NTLM authentication. Some
applications will automatically use the user's credentials to perform the
authentication in the background, without checking whether this service is
legit or malicious. Sometimes even for services on the internet.

To mitigate this situation, you could disable NTLM and use Kerberos
everywhere instead. If, and that's a big if, all your devices support
Kerberos. Simply using strong passwords on `all` accounts is arguably more
feasible.


Kerberoasting
-------------

`Kerberoasting <https://attack.mitre.org/techniques/T1558/003/>`_ is an
attack that anyone with domain credentials can perform. It works by
requesting service tickets for all accounts that have a service principal
name registered on them. These tickets are encrypted with the password of
the corresponding account, so the attacker can use them to perform an
offline password guessing attack.

Accounts compromised by kerberoasting often have at least admin privileges
on the machine that the associated service is running on. Sometimes they
are even more powerful.

Requesting a service ticket is a normal process and there is nothing you can
do about it. Sure, someone requesting 20 tickets within a single second
should raise some flags, but if they request one ticket per day (or if you
don't monitor such events at all), then the only thing that's saving you is
using strong passwords. Well, and not using domain admins for any old
service out there, but that's also a different story.


Domain Cached Credentials
-------------------------

It shouldn't happen, but it does: A server gets compromised and someone who
shouldn't even be on it gains admin permissions. Maybe it's a server that
some intern set up a while ago which runs an old Tomcat instance with the
default password still set. Or it's some other long-forgotten project by
someone who isn't even in the company anymore and which somehow hasn't
received a Windows security update since 2016.

The thing is, if somebody logs onto the server, Windows caches the
credentials on it. You know, just in case the domain controllers are
unavailable at some point in the future when you want to logon again.
Someone with admin privileges can extract them and perform an offline
password guessing attack. The cached credentials are hashed using a salt and
a cost factor, so cracking them is *hard* -- but they can be cracked, if the
password is sufficiently weak.

You can reduce the maximum number of cached credentials on servers, which is
set to ten by default. It makes sense to allow one or two sets of
credentials on laptops, but servers are unlikely to lose connection to
the domain controller, so setting them to zero shouldn't be a problem.

Oooor you could just have everybody use strong passwords. Ideally, do both.


How do offline password guessing attacks work?
==============================================

First of all, they rarely work by using brute force. By "brute force" I mean
simply trying out every combination of characters there is. Yes,
theoretically you will crack any hash this way, but realistically the sun
will explode first.

.. note::
   There are some really creative hashing algorithms out there that
   severely limit the size of the password space where brute force will
   actually work, but those are rarely relevant. I am, of course, referring
   to the infamous LM hash algorithm, but in the vast majority of situations
   in which you obtain an LM hash, you also obtain the corresponding NT hash,
   which can be used for the `pass-the-hash
   <https://en.wikipedia.org/wiki/Pass_the_hash>`_ technique, which means
   you don't even need to crack the password. The hash already *is* the
   password in some sense.

What any attacker worth their salt does is to emulate the decision process
that a human being uses to choose a password. A human being typically thinks
of a word first, and because the human mind is a bad random generator, it
will think of a name of a loved one or some really common word first. The
company wants them to choose a password, so the name of the company comes to
mind quickly. An animal, an color, or something that is typically right in
front you when you choose the password, like "table", "lamp", "sun", are
also popular choices. The company also wants them to choose a *new* password
every 90 days, so one of the seasons may come to mind. The company wants them
to use numbers, too, so they append the current year, someone's birth year
or just a ``1`` at the end. Oh, a special character is also required?
`Fine`, let's append an exclamation mark.

.. note::
   Expiring passwords are falling out of fashion these days. `NIST
   <https://pages.nist.gov/800-63-3/sp800-63b.html>`_ was the organization
   recommending a maximum password age of 90 days, but has since changed
   their mind. It has become clear that this practice leads to users
   choosing less secure passwords. `Microsoft
   <https://docs.microsoft.com/en-us/archive/blogs/secguide/security-baseline-final-for-windows-10-v1903-and-windows-server-v1903>`_
   has followed suit and removed the recommendations from their security
   baseline:

       `Periodic password expiration is an ancient and obsolete mitigation of
       very low value`

Even if the users take a little more time, they will probably choose a word
that is in the dictionary. In an effort to make it a little more secure,
they replace an ``o`` by a ``0``, or an ``a`` by an ``@``. Or they will use
the same word twice. Or a pattern on their keyboard. You get the idea.

Attackers know this and start off with a huge list of words. These can be
dictionary words, but also passwords from past breaches that have gone
public. One of the biggest one was a social site named RockYou, where 32
million passwords leaked. The kicker is: They weren't hashed at all, so
these are real passwords that humans chose, unbiased by what someone was
able to crack. Turns out, we are not so unique as we often like to think,
and we often choose the same passwords.

Other things that are good for a dictionary attack: Phrases from `books
<https://www.gutenberg.org>`_, Wikipedia (all languages), Tweets, YouTube
comments, etc.

But attackers don't just apply the list and call it a day. They use rules
to mangle the passwords. Reverse them, change the capitalization, append
numbers, replace characters, combine them, repeat them, and so on. And they
do this very successfully. Just read `this impressive article
<https://arstechnica.com/information-technology/2013/10/how-the-bible-and-youtube-are-fueling-the-next-frontier-of-password-cracking/>`_ about what
kinds of passwords can be cracked. My favorites:

* ``Msy919asdfgzxcvb``
* ``N3v3rmarrydorian``
* ``Sadly second episode is of very poor sound quality.``
* ``ZSE$5rdxCFT^7ygv``

Note that the last one satisfies even the most draconian password policies.

Surprised? You should be. I was. Wondering if your password has been leaked
already in one of the many breaches in the past years? Go check at `Have I
been pwned? <https://haveibeenpwned.com/>`_. Don't worry, it's done in a
clever and secure way, so it's safe to put your password in there, even
though I more than understand if you're feeling wary about putting your
password into some site on the internet.

The equipment needed to crack a hash is not special. Sure, top-of-the-line
graphics cards help a lot, but these days you can also just rent
computational power from the cloud provider of your choosing. Even with a
regular laptop you can compute quite a few hashes per second.


So what is a secure password?
=============================

The bad news first. Honestly, only a randomly generated password is secure.
Unfortunately, the good passwords are precisely those that are hard to
remember. And at the same time, you can't reuse them.

`Diceware <https://en.wikipedia.org/wiki/Diceware>`_ is fine if you don't
like random strings of characters, but remembering lots of passphrases that
consist of six `random` words is not that easy either, especially if you
need some of them not that frequently. Some password generators produce
random but still somehow pronounceable passwords by stringing together
random syllables. This has less entropy compared to a completely random
string, so make them a bit longer.

Still, there is basically no way around a password manager, and even then
you probably need to remember a few passwords. Typically the one for the
password manager itself, obviously, then the logon password to your
computer, and possibly the password for the hard drive encryption (which
everybody should have). Once at work, once at home.

The good news is that these are passwords that you will use several times a
day, every day. So even if they are random strings or words, you will
quickly remember them. Maybe write them down for a day or two, but keep it
in your wallet and then destroy the note securely.

To boil it down:

.. admonition:: The Three Password Rules

   * `Generate` strong passwords
   * Don't reuse them
   * Use a password manager



How do I get my users to use secure passwords?
==============================================

Using a password manager is the easy part.

The real challenge begins when you are responsible for many users and want
`them` to use secure passwords, at least in your Active Directory. At this
point I shouldn't have to explain why requiring a minimal password length
and a certain password complexity isn't the solution.

The next best thing you can do is to use a `password filter
<https://docs.microsoft.com/en-us/windows/win32/secmgmt/password-filters>`_
that checks the password against a list of forbidden words in the moment the
user sets the password. However, there are a few problems with it.

1. It requires a third party product, possibly closed source, to be
   installed on your domain controllers, because Active Directory does not
   support this feature out of the box. (Azure AD does, though.) Not an
   issue on its own, but it does increase the attack surface.
2. While the check may be case insensitive and consider common character
   replacements, it is no substitute for the vast rule sets that come with
   state-of-the-art crackers. Some of those solution even only check against
   a list of breached hashes, so they will not catch slight variations of
   breached hashes -- but hackers will.
3. The filter may catch passwords that are perfectly fine. A user may choose
   a lengthy passphrase such as "Paradox Trouble Childcare Summer Alibi
   Consonant", which no one will ever crack, but because it contains the
   blacklisted word 'Summer', it won't pass the filter. This is
   unnecessarily frustrating to your users.
4. It is only proactive, not reactive. You won't be able to identify old
   accounts with weak passwords, unless you force a reset on all of them.

So what can you do? The answer is: You do the same thing an attacker would
do. Be one step ahead. **Regularly attempt to crack your users' passwords.**

Enter Crack-O-Matic.


How it works
============

Crack-O-Matic provides a web application based on Python-Flask for
scheduling either recurring or one-time audits.

In the background, Crack-O-Matic uses `Samba <https://www.samba.org/>`_ to
initiate a domain controller replication. However, only the user database
is transferred. No computer object is added to Active Directory. In fact, no
modifications are made whatsoever.

Then, either `John the Ripper <https://www.openwall.com/john/>`_ or `Hashcat
<https://hashcat.net/hashcat/>`_ are used to perform the password guessing
attack and crack those hashes. Depending on your hardware you can easily
check billions of password candidates per second.

Finally, users whose passwords have been cracked are notified by e-mail.
Optionally, the admin will receive a list of their account names by e-mail.
A report and a statistical analysis will be available in the web front-end.
