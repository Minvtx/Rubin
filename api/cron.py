from http.server import BaseHTTPRequestHandler
import sys
import os

# Add the root directory to sys.path so we can import from main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import RubinAgent

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print("Vercel Cron triggered Rubin Agent")
            
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            agent = RubinAgent(
                config_path=os.path.join(root_dir, "config.json"), 
                system_prompt_path=os.path.join(root_dir, "system_prompt.md"), 
                seeds_path=os.path.join(root_dir, "seeds.json")
            )
            
            # Note: Serverless environments have low timeouts (e.g. 10s on Vercel Hobby).
            # We don't use jitter/sleep here.
            thought = agent.run_once()
            
            if thought:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Executed single run successfully. Thought length: {len(thought)}".encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Error: Failed to generate thought.")
                
        except Exception as e:
            import traceback
            error_msg = f"Error in Vercel Cron execution: {e}\n{traceback.format_exc()}"
            print(error_msg)
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(error_msg.encode('utf-8'))
