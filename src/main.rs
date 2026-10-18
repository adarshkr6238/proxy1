use tokio::net::{TcpListener, TcpStream};
use tokio::io::copy_bidirectional;
use std::env;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let port = env::var("PORT").unwrap_or_else(|_| "7860".to_string());
    let listen_addr = format!("0.0.0.0:{}", port);
    let target_addr = "api.telegram.org:443";
    
    let listener = TcpListener::bind(&listen_addr).await?;
    println!("Listening on {}, proxying to {}", listen_addr, target_addr);

    loop {
        let (mut client_stream, _) = listener.accept().await?;
        let target_stream = TcpStream::connect(target_addr).await?;
        tokio::spawn(async move {
            let mut target_stream = target_stream;
            let _ = copy_bidirectional(&mut client_stream, &mut target_stream).await;
        });
    }
}
