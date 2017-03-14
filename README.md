# podcast-python
Script for automating the uploading of a new podcast
 
This script:

1. Gets information such as duration from MP3 file
2. Allows user to input additional information (title, etc.)
3. Updates iTunes XML podcast file
4. Concatenates MP3 file with intro and outro segments
5. Creates OGG file version
6. Uploads XML and MP3 and OGG files to Amazon S3 and makes PUBLIC

Requires:

- boto   https://github.com/boto/boto.git
- mpeg1audio   https://github.com/Ciantic/mpeg1audio/
- pydub (which requires ffmpeg to be installed) https://github.com/jiaaro/pydub
- Edited MP3 file
- MP3 intro and outro segments
- Image file public on S3
- header XML in header txt file
- text file to store individual podcast XML, even if initially (mostly) empty. 
-     Needs lines:
-       </channel>
-       </rss>
- An existing RSS podcast feed XML file (or a null file)
- Existing AWS S3 bucket and credentials
- Supporting files in same directory as MP3 file
- set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables
- Redefine the global filename variables for your needs
- Redefine the bucket name for your needs


