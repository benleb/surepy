.. role:: raw-html-m2r(raw)
   :format: html



.. image:: https://socialify.git.ci/benleb/surepy/image?description=1&descriptionEditable=Library%20%26%20CLI%20to%20interact%20with%20the%20Sure%20Petcare%20API%20to%20monitor%20and%20control%20the%20Sure%20Petcare%20Pet%20Door%2FCat%20Flap%20Connect%20%F0%9F%9A%AA%20and%20the%20Pet%20Feeder%20Connect%20%F0%9F%8D%BD&font=KoHo&forks=1&language=1&logo=https%3A%2F%2Femojipedia-us.s3.dualstack.us-west-1.amazonaws.com%2Fthumbs%2F240%2Fapple%2F237%2Fpaw-prints_1f43e.png&pulls=1&stargazers=1
   :target: https://github.com/benleb/surepy
   :alt: surepy

=========================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================

Library & CLI to interact with the Sure Petcare API. `\ **surepy** <https://github.com/benleb/surepy>`_ lets you monitor and control the Pet Door/Cat Flap Connect 🚪 and the Pet Feeder Connect 🍽 by `Sure Petcare <https://www.surepetcare.com>`_.

`\ **surepy** <https://github.com/benleb/surepy>`_ can...

🔑 **get an api token** with your account credentials\ :raw-html-m2r:`<br>`
🚪 **lock/unlock** a door or flap\ :raw-html-m2r:`<br>`
🐾 get the **location** of **pets** & **devices**\ :raw-html-m2r:`<br>`
🐈 get the **state** and more attributes of **pets** & **devices**\ :raw-html-m2r:`<br>`
🕰️ get **historic** data & events of pets & devices\ :raw-html-m2r:`<br>`
📬 get a list of (past) **notifications**  


.. raw:: html

   <!-- > **ToC ·** [Getting Started](#getting-started) · [Usage](#usage)· [Used by](#used-by) · [Acknowledgements](#acknowledgements) **·** [Meta](#meta) -->



Getting Started
---------------

Currently `\ **surepy** <https://github.com/benleb/surepy>`_ is only distributed via `pypi.org <https://pypi.org>`_. Maybe there will be a little Docker Image eventually.

Install via `pypi.org <https://pypi.org>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python3 -m pip install --upgrade surepy
   # or
   pip install --upgrade surepy

Usage
-----

*needs a little more documentation maybe...*

CLI
^^^

*the cli probably has some bugs, be careful* 🐾

.. code-block:: bash

   surepy --help

Library
^^^^^^^

see (the not yet written) `docs <https://surepy.readthedocs.io/en/latest/>`_

----

Used by
-------


* `Sure Petcare <https://www.home-assistant.io/integrations/surepetcare/>`_ integration in `Home Assistant <https://www.home-assistant.io/>`_

Feel free to add you project!

Acknowledgments
---------------


* Thanks to all the people who provided information about devices I do not own myself, thanks!
* Thanks to `@rcastberg <https://github.com/rcastberg>`_ for hist previous work on the `Sure Petcare <https://www.surepetcare.com>`_ API (\ `github.com/rcastberg/sure_petcare <https://github.com/rcastberg/sure_petcare>`_\ )
* Thanks to `@wei <https://github.com/wei>`_ for the  header image generator (\ `github.com/wei/socialify <https://github.com/wei/socialify>`_\ )

Meta
----

**Ben Lebherz**\ : *cat lover 🐾 developer & maintainer* - `@benleb <https://github.com/benleb>`_ | `@ben_leb <https://twitter.com/ben_leb>`_


.. raw:: html

   <!-- See also the list of [contributors](CONTRIBUTORS) who participated in this project. -->



This project is licensed under the MIT License - see the `LICENSE <LICENSE>`_ file for details
